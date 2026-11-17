from odoo.tests import tagged
from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestPhase3Architecture(FeedbackTestCommon):
    def test_rating_is_native_source_of_truth(self):
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 4,
            'review_text': 'A sufficiently long review for architecture testing.',
        })
        self.assertTrue(review.rating_id)
        self.assertEqual(review.rating, 4.0)
        self.assertEqual(review.rating_id.feedback_review_id, review)
        self.assertFalse(review._fields['rating'].store)

    def test_moderation_changes_native_consumption_not_rating_rows(self):
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_text': 'Another sufficiently long review for architecture testing.',
        })
        native_id = review.rating_id.id
        review.action_approve()
        self.assertTrue(review.rating_id.consumed)
        review.action_reject()
        self.assertEqual(review.rating_id.id, native_id)
        self.assertFalse(review.rating_id.consumed)
