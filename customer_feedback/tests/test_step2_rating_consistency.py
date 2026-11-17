# -*- coding: utf-8 -*-
"""Step 2 — Native rating_avg/rating_count must match approved feedback.review.

Prevents disagreement between:
  - website list: feedback.review WHERE status='approved'
  - native stars: product.template.rating_avg / rating_count
    (from rating.rating WHERE consumed=True)
"""
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestStep2RatingConsistency(FeedbackTestCommon):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.moderation_enabled', 'True')
        self.tmpl = self.product.product_tmpl_id

    def _approved(self, rating=5):
        request = self._create_request()
        if self.env['feedback.review'].search([('request_id', '=', request.id)], limit=1):
            request = self.env['feedback.request'].create({
                'sale_order_id': self.sale_order.id,
                'sale_order_line_id': self.sale_order.order_line[:1].id,
                'partner_id': self.customer.id,
                'product_id': self.product.id,
                'company_id': self.sale_order.company_id.id,
            })
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'rating': rating,
            'review_title': 'Step2',
            'review_text': 'Approved verified review body with enough length.',
        })
        review.action_approve()
        return review

    def test_01_approved_count_matches_native_rating_count(self):
        self._approved(5)
        self._approved(3)
        self.tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        stats = self.env['feedback.review']._assert_native_matches_approved(self.tmpl)
        self.assertTrue(stats['match'])
        self.assertEqual(stats['approved_reviews'], 2)
        self.assertEqual(stats['rating_count'], 2)
        self.assertAlmostEqual(stats['rating_avg'], 4.0, places=2)

    def test_02_shared_mode_preserves_unowned_native_rating(self):
        """Default shared mode: unowned native ratings stay consumed and count."""
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.rating_ownership', 'shared')
        self.assertEqual(
            self.env['feedback.review']._get_rating_ownership(), 'shared')

        foreign = self.env['rating.rating'].sudo().create({
            'res_model_id': self.env['ir.model']._get_id('product.template'),
            'res_model': 'product.template',
            'res_id': self.tmpl.id,
            'partner_id': self.customer.id,
            'rating': 1.0,
            'consumed': True,
            'feedback': 'Legacy free-form rating',
        })
        self.assertFalse(foreign.feedback_review_id)

        self._approved(5)

        result = self.env['feedback.review']._reconcile_product_native_ratings()
        self.assertEqual(result.get('deactivated_foreign', 0), 0)
        self.assertEqual(result.get('ownership'), 'shared')

        foreign.invalidate_recordset(['consumed'])
        self.assertTrue(
            foreign.consumed,
            'Shared mode must not deactivate unowned native product ratings',
        )

        self.tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        # Both foreign (1★) and approved (5★) contribute → count 2, avg 3.0
        self.assertEqual(self.tmpl.rating_count, 2)
        self.assertAlmostEqual(self.tmpl.rating_avg, 3.0, places=2)

    def test_02b_exclusive_mode_deactivates_unowned_product_rating(self):
        """Exclusive opt-in: unowned product ratings are excluded from aggregates."""
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.rating_ownership', 'exclusive')
        self.assertEqual(
            self.env['feedback.review']._get_rating_ownership(), 'exclusive')

        foreign = self.env['rating.rating'].sudo().create({
            'res_model_id': self.env['ir.model']._get_id('product.template'),
            'res_model': 'product.template',
            'res_id': self.tmpl.id,
            'partner_id': self.customer.id,
            'rating': 1.0,
            'consumed': True,
            'feedback': 'Legacy free-form rating',
        })
        self.assertFalse(foreign.feedback_review_id)

        self._approved(5)

        result = self.env['feedback.review']._reconcile_product_native_ratings()
        self.assertGreaterEqual(result['deactivated_foreign'], 1)
        self.assertEqual(result.get('ownership'), 'exclusive')

        foreign.invalidate_recordset(['consumed'])
        self.assertFalse(
            foreign.consumed,
            'Exclusive mode must set unowned product rating consumed=False',
        )

        self.tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        stats = self.env['feedback.review']._assert_native_matches_approved(self.tmpl)
        self.assertTrue(stats['match'])
        self.assertEqual(stats['rating_count'], 1)
        self.assertAlmostEqual(stats['rating_avg'], 5.0, places=2)

    def test_03_unrelated_model_rating_is_never_deactivated(self):
        """Ownership applies only to product.template ratings."""
        model_id = self.env['ir.model']._get_id('res.partner')
        foreign = self.env['rating.rating'].sudo().create({
            'res_model_id': model_id,
            'res_model': 'res.partner',
            'res_id': self.customer.id,
            'partner_id': self.customer.id,
            'rating': 1.0,
            'consumed': True,
            'feedback': 'Unrelated model rating',
        })
        self.env['feedback.review']._reconcile_product_native_ratings()
        foreign.invalidate_recordset(['consumed'])
        self.assertTrue(
            foreign.consumed,
            'Exclusive product ownership must never alter ratings on other models',
        )

    def test_04_rejected_review_does_not_count_in_native(self):
        review = self._approved(4)
        review.action_reject()
        self.tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        stats = self.env['feedback.review']._assert_native_matches_approved(self.tmpl)
        self.assertTrue(stats['match'])
        self.assertEqual(stats['rating_count'], 0)

    def test_05_reconcile_is_idempotent(self):
        self._approved(5)
        r1 = self.env['feedback.review']._reconcile_product_native_ratings()
        r2 = self.env['feedback.review']._reconcile_product_native_ratings()
        self.assertEqual(r2['bridged'], 0)
        self.assertEqual(r2['deactivated_foreign'], 0)
        stats = self.env['feedback.review']._assert_native_matches_approved(self.tmpl)
        self.assertTrue(stats['match'])

    def test_06_linked_non_approved_consumed_flag_fixed(self):
        review = self._approved(5)
        # Simulate drift: approved review but consumed=False
        review.rating_id.sudo().write({'consumed': False})
        self.env['feedback.review']._sync_approved_consumed_flags()
        self.assertTrue(review.rating_id.consumed)
        self.tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(self.tmpl.rating_count, 1)

    def test_07_default_ownership_is_shared(self):
        """Missing or invalid ICP falls back to shared."""
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('customer_feedback.rating_ownership', False)
        # delete key
        param = icp.search([('key', '=', 'customer_feedback.rating_ownership')], limit=1)
        if param:
            param.unlink()
        self.assertEqual(
            self.env['feedback.review']._get_rating_ownership(), 'shared')
        icp.set_param('customer_feedback.rating_ownership', 'bogus')
        self.assertEqual(
            self.env['feedback.review']._get_rating_ownership(), 'shared')

    def test_08_shared_mode_does_not_reactivate_historical(self):
        """Shared mode never mass-reactivates consumed=False historical rows."""
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.rating_ownership', 'shared')
        historical = self.env['rating.rating'].sudo().create({
            'res_model_id': self.env['ir.model']._get_id('product.template'),
            'res_model': 'product.template',
            'res_id': self.tmpl.id,
            'partner_id': self.customer.id,
            'rating': 2.0,
            'consumed': False,
            'feedback': 'Previously deactivated for unrelated reason',
        })
        self.env['feedback.review']._reconcile_product_native_ratings()
        historical.invalidate_recordset(['consumed'])
        self.assertFalse(
            historical.consumed,
            'Shared mode must not mass-reactivate historical consumed=False rows',
        )
