from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestFeedbackReview(FeedbackTestCommon):

    def _review_vals(self, request, **overrides):
        vals = {
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_title': 'Great product',
            'review_text': 'This product exceeded my expectations by far.',
        }
        vals.update(overrides)
        return vals

    def test_01_rating_required(self):
        request = self._create_request()
        vals = self._review_vals(request)
        del vals['rating']
        with self.assertRaises(Exception):
            self.env['feedback.review'].create(vals)

    def test_02_rating_out_of_range_rejected(self):
        request = self._create_request()
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create(self._review_vals(request, rating=6))
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create(self._review_vals(request, rating=0))

    def test_03_rating_in_range_accepted(self):
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request, rating=4))
        self.assertEqual(review.rating, 4)

    def test_04_review_text_too_short_rejected(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.review_min_length', '10')
        request = self._create_request()
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create(self._review_vals(request, review_text='short'))

    def test_05_review_text_too_long_rejected(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.review_max_length', '50')
        request = self._create_request()
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create(
                self._review_vals(request, review_text='x' * 51))

    def test_06_duplicate_review_per_request_blocked(self):
        request = self._create_request()
        self.env['feedback.review'].create(self._review_vals(request))
        with self.assertRaises(Exception):
            self.env['feedback.review'].create(self._review_vals(request))

    def test_07_moderation_enabled_sets_pending(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'True')
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))
        self.assertEqual(review.status, 'pending')

    def test_08_moderation_disabled_auto_approves(self):
        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'False')
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))
        self.assertEqual(review.status, 'approved')

    def test_09_moderator_actions(self):
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))
        review.action_approve()
        self.assertEqual(review.status, 'approved')
        review.action_reject()
        self.assertEqual(review.status, 'rejected')
        review.action_hide()
        self.assertEqual(review.status, 'hidden')

    def test_10_customer_edit_updates_in_place(self):
        """Editing must update the existing review, never create a second
        one for the same request."""
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request, rating=3))
        review.action_customer_edit({'rating': 5, 'review_title': 'Updated title'})
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.review_title, 'Updated title')
        count = self.env['feedback.review'].search_count([('request_id', '=', request.id)])
        self.assertEqual(count, 1)

    def test_11_anonymous_display_modes(self):
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))

        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.anonymous_display', 'full')
        self.assertEqual(review.get_display_name_public(), self.customer.name)

        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.anonymous_display', 'anonymous')
        self.assertEqual(review.get_display_name_public(), 'Anonymous Customer')

        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.anonymous_display', 'masked')
        masked = review.get_display_name_public()
        self.assertNotEqual(masked, self.customer.name)
        self.assertTrue(masked.startswith(self.customer.name.split()[0]))

    def test_12_restore_brings_review_back_to_approved(self):
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))
        review.action_hide()
        self.assertEqual(review.status, 'hidden')
        review.action_restore()
        self.assertEqual(review.status, 'approved')

    def test_13_moderator_group_can_moderate_but_not_delete_or_create(self):
        """SRS Section 9/17 'Review Moderator' actor: can read/approve/reject/
        hide/restore any review, but cannot delete reviews or create them
        directly (customers submit reviews through the token-secured portal
        flow, not the moderator)."""
        moderator_user = self.env['res.users'].create({
            'name': 'Test Moderator',
            'login': 'test_moderator@example.com',
            'email': 'test_moderator@example.com',
            'groups_id': [(6, 0, [self.env.ref('customer_feedback.group_feedback_moderator').id])],
        })
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))

        review_as_moderator = review.with_user(moderator_user)
        review_as_moderator.action_approve()
        self.assertEqual(review.status, 'approved')

        with self.assertRaises(Exception):
            review_as_moderator.unlink()

        with self.assertRaises(Exception):
            self.env['feedback.review'].with_user(moderator_user).create(
                self._review_vals(request, rating=3))

    def test_14_plain_user_group_cannot_moderate(self):
        """The read-only Feedback User group must not be able to change a
        review's status - only Moderator/Manager can."""
        plain_user = self.env['res.users'].create({
            'name': 'Test Read Only',
            'login': 'test_readonly@example.com',
            'email': 'test_readonly@example.com',
            'groups_id': [(6, 0, [self.env.ref('customer_feedback.group_feedback_user').id])],
        })
        request = self._create_request()
        review = self.env['feedback.review'].create(self._review_vals(request))

        with self.assertRaises(Exception):
            review.with_user(plain_user).action_approve()
