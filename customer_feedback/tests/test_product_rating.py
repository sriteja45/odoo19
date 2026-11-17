from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestProductRating(FeedbackTestCommon):

    def test_01_rating_stats_recomputed_on_approval(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'False')
        request = self._create_request()
        self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 4,
            'review_text': 'Solid product, would recommend to a friend.',
        })
        tmpl = self.product.product_tmpl_id
        self.assertEqual(tmpl.rating_count, 1)
        self.assertEqual(tmpl.rating_avg, 4.0)
        self.assertEqual(tmpl.get_rating_distribution().get(4, 0), 1)

    def test_02_rejected_review_excluded_from_stats(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'True')
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 1,
            'review_text': 'Not what I expected from this purchase at all.',
        })
        review.action_reject()
        tmpl = self.product.product_tmpl_id
        self.assertEqual(tmpl.rating_count, 0)

    def test_03_unlink_recomputes_stats(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'False')
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_text': 'Excellent quality and fast delivery, very satisfied.',
        })
        tmpl = self.product.product_tmpl_id
        self.assertEqual(tmpl.rating_count, 1)
        native_rating = review.rating_id
        review.unlink()
        self.assertEqual(tmpl.rating_count, 0)
        self.assertEqual(tmpl.rating_avg, 0.0)
        self.assertTrue(native_rating.exists())
        self.assertFalse(native_rating.consumed)
