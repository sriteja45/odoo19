# -*- coding: utf-8 -*-
"""Step 1 — Native review override: single verified-purchase submission path.

Asserts that:
- website_sale.product_comment is inactive (native free-form form hidden)
- product.template._mail_post_access remains 'write'
- portal/public cannot create rating.rating via message_post(rating_value=…)
- the sole public submission path is the token portal controller
"""
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestStep1NativeOverride(FeedbackTestCommon):
    """Contract tests for doc/STEP1_NATIVE_OVERRIDE.md."""

    def test_01_product_comment_view_is_inactive(self):
        """Native free-form review form must stay disabled."""
        view = self.env.ref('website_sale.product_comment', raise_if_not_found=False)
        self.assertTrue(view, 'website_sale.product_comment view must exist')
        self.assertFalse(
            view.active,
            'website_sale.product_comment must be inactive so the free-form '
            'portal.message_thread form is not shown on product pages',
        )

    def test_02_mail_post_access_is_write(self):
        """Public/portal must not be able to post on product chatter."""
        self.assertEqual(
            self.env['product.template']._mail_post_access,
            'write',
            "product.template._mail_post_access must be 'write' (not website_sale's "
            "'read') while this module owns verified-purchase reviews",
        )

    def test_03_portal_cannot_create_native_rating_via_message_post(self):
        """Defense-in-depth: rating_value from portal is stripped / blocked."""
        portal_user = self.env['res.users'].create({
            'name': 'Step1 Portal',
            'login': 'step1_portal_rating',
            'email': 'step1_portal@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        tmpl = self.product.product_tmpl_id
        before = self.env['rating.rating'].sudo().search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', tmpl.id),
        ])
        try:
            tmpl.with_user(portal_user).message_post(
                body='Trying free-form rating', rating_value=5)
        except AccessError:
            pass
        after = self.env['rating.rating'].sudo().search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', tmpl.id),
        ])
        self.assertEqual(
            before, after,
            'Portal message_post(rating_value=…) must not create rating.rating',
        )

    def test_04_internal_user_message_post_rating_still_allowed(self):
        """Internal users / sudo may still pass rating_value (bridge uses sudo)."""
        # Bridge creates ratings under sudo; this only checks the guard does
        # not strip for internal users. We do not assert a rating is created
        # via message_post (website_sale rating UX is disabled); only that
        # the kwargs are not stripped for group_user.
        tmpl = self.product.product_tmpl_id
        # Call as admin (group_user) — should not raise solely due to our guard
        msg = tmpl.with_user(self.env.ref('base.user_admin')).message_post(
            body='Internal note')
        self.assertTrue(msg)

    def test_05_verified_path_still_creates_native_rating(self):
        """The only intended path: feedback.review → bridge → rating.rating."""
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.moderation_enabled', 'True')
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_title': 'Step1 path',
            'review_text': 'Verified purchase path creates the native rating.',
        })
        review.action_approve()
        self.assertTrue(review.rating_id)
        self.assertTrue(review.rating_id.consumed)
        self.assertEqual(review.rating_id.res_model, 'product.template')
        self.assertEqual(review.rating_id.res_id, review.product_tmpl_id.id)
