from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestRatingBridge(FeedbackTestCommon):
    """Coverage for rating_bridge.py (feedback.review <-> rating.rating) and
    the Phase 3 hardening in product_template.py that prevents the native
    chatter route from creating an unmoderated rating.rating directly.

    This closes the gap flagged in the Phase 1 audit: the bridge was the
    newest, most architecturally important code in the module but had no
    dedicated tests.
    """

    def _approved_review(self, rating=5):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'True')
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': rating,
            'review_title': 'Great product',
            'review_text': 'This exceeded my expectations by quite a bit.',
        })
        review.action_approve()
        return review

    # -- bridge: approve -> native rating -------------------------------

    def test_01_approval_creates_linked_native_rating(self):
        review = self._approved_review(rating=4)
        self.assertTrue(review.rating_id, 'Approving a review should create/link a rating.rating.')
        self.assertEqual(review.rating_id.res_model, 'product.template')
        self.assertEqual(review.rating_id.res_id, review.product_tmpl_id.id)
        self.assertTrue(review.rating_id.consumed, 'Approved reviews must be consumed=True so they count natively.')
        self.assertEqual(review.rating_id.rating, 4.0)

    def test_02_native_average_matches_approved_reviews(self):
        self._approved_review(rating=4)
        review2 = self.env['feedback.request']
        # second delivered line for the same product/customer via a fresh request
        request2 = self.env['feedback.request'].create({
            'sale_order_id': self.sale_order.id,
            'sale_order_line_id': self.env['sale.order.line'].create({
                'order_id': self.sale_order.id,
                'product_id': self.product.id,
                'product_uom_qty': 1,
            }).id,
            'partner_id': self.customer.id,
            'product_id': self.product.id,
            'company_id': self.sale_order.company_id.id,
        })
        review2 = self.env['feedback.review'].create({
            'request_id': request2.id,
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'rating': 2,
            'review_text': 'It was okay, not great, had some issues.',
        })
        review2.action_approve()

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 2)
        self.assertAlmostEqual(tmpl.rating_avg, 3.0, places=2)

    def test_03_rejecting_excludes_from_native_average_but_keeps_row(self):
        review = self._approved_review(rating=5)
        rating_id = review.rating_id
        self.assertTrue(rating_id.consumed)

        review.action_reject()
        self.assertEqual(review.rating_id.id, rating_id.id, 'Rejecting should not unlink the native rating row.')
        self.assertFalse(review.rating_id.consumed, 'Rejected reviews must not count toward the native average.')

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 0)

    def test_04_unlink_preserves_native_rating_history(self):
        review = self._approved_review(rating=5)
        rating = review.rating_id
        review.unlink()
        self.assertTrue(rating.exists(), 'Deleting a review must preserve the native rating row.')
        self.assertFalse(rating.consumed, 'A native rating retained after review deletion must be de-consumed.')
        self.assertFalse(rating.feedback_review_id, 'The deleted business review must no longer own the native rating.')

    def test_05_explicit_internal_purge_removes_native_rating(self):
        review = self._approved_review(rating=5)
        rating = review.rating_id
        review.with_context(permanent_rating_purge=True).unlink()
        self.assertFalse(rating.exists(), 'Physical native-rating deletion must require explicit internal purge.')

    def test_06_bridge_all_approved_is_idempotent(self):
        review = self._approved_review(rating=3)
        first_rating_id = review.rating_id.id

        bridged = self.env['feedback.review']._bridge_all_approved_to_native_rating()
        self.assertEqual(bridged, 0, 'Nothing should need (re)bridging; the review is already linked.')
        self.assertEqual(review.rating_id.id, first_rating_id, 'Re-running the bridge must not create duplicates.')

        native_count = self.env['rating.rating'].search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', review.product_tmpl_id.id),
        ])
        self.assertEqual(native_count, 1)

    # -- Phase 3 hardening: native chatter can't create ratings directly --

    def test_07_message_post_rating_value_stripped_for_non_internal(self):
        """A non-internal / non-sudo caller passing rating_value to
        message_post() on a product must not be able to create a native
        rating.rating outside the moderation bridge (see product_template.py
        message_post override + _mail_post_access = 'write')."""
        portal_user = self.env['res.users'].create({
            'name': 'Portal Caller',
            'login': 'portal_caller_ratingtest',
            'email': 'portal_caller@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        tmpl = self.product.product_tmpl_id
        before = self.env['rating.rating'].sudo().search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', tmpl.id),
        ])
        try:
            tmpl.with_user(portal_user).message_post(body='Great product!', rating_value=5)
        except AccessError:
            # Also an acceptable outcome: the ORM/ACL layer blocked the post
            # entirely before our rating_value guard was even needed.
            pass
        after = self.env['rating.rating'].sudo().search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', tmpl.id),
        ])
        self.assertEqual(before, after, 'A portal/public rating_value post must not create a rating.rating.')

    def test_08_mail_post_access_is_not_public_read(self):
        """Guard against a future regression silently re-lowering
        _mail_post_access back to website_sale's native 'read' default,
        which is what originally made the native chatter route reachable by
        any visitor."""
        self.assertEqual(
            self.env['product.template']._mail_post_access, 'write',
            "product.template._mail_post_access must stay 'write' so public/portal "
            "users cannot post on (and rate) products through the native chatter route."
        )
