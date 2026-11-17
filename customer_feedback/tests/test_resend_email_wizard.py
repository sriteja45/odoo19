from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestResendEmailWizard(FeedbackTestCommon):

    def test_01_resend_invitation_attempts_send(self):
        """Resending should make an attempt (success or logged failure,
        depending on whether SMTP is configured in this environment) and
        move invitation_email_status out of its initial 'pending' state."""
        request = self._create_request()
        wizard = self.env['feedback.resend.email.wizard'].create({
            'request_ids': [(6, 0, [request.id])],
            'email_type': 'invitation',
        })
        wizard.action_resend()
        self.assertIn(request.invitation_email_status, ('sent', 'failed', 'retried'))

    def test_02_reset_retry_count_clears_exhausted_counter(self):
        """A request that already exhausted its retries (as the cron would
        leave it) must be resettable so it can be attempted again."""
        request = self._create_request()
        request.write({'invitation_email_status': 'failed', 'invitation_retry_count': 3})
        wizard = self.env['feedback.resend.email.wizard'].create({
            'request_ids': [(6, 0, [request.id])],
            'email_type': 'invitation',
            'reset_retry_count': True,
        })
        wizard.action_resend()
        # The counter was reset to 0 before the new attempt; a single retry
        # (success or fresh failure) means it can only be 0 or 1 afterwards,
        # never left at the old exhausted value of 3.
        self.assertIn(request.invitation_retry_count, (0, 1))

    def test_03_submitted_requests_are_not_eligible(self):
        """A request whose review was already submitted must be skipped,
        and if it's the only one selected, the wizard should refuse."""
        request = self._create_request()
        self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_title': 'Great',
            'review_text': 'Exceeded expectations by a wide margin.',
        })
        self.assertEqual(request.status, 'submitted')

        wizard = self.env['feedback.resend.email.wizard'].create({
            'request_ids': [(6, 0, [request.id])],
            'email_type': 'invitation',
        })
        with self.assertRaises(UserError):
            wizard.action_resend()

    def test_04_reminder_type_targets_reminder_fields(self):
        request = self._create_request()
        request.write({'status': 'sent', 'reminder_email_status': 'failed', 'reminder_retry_count': 2})
        wizard = self.env['feedback.resend.email.wizard'].create({
            'request_ids': [(6, 0, [request.id])],
            'email_type': 'reminder',
            'reset_retry_count': True,
        })
        wizard.action_resend()
        self.assertIn(request.reminder_email_status, ('sent', 'failed', 'retried'))
        # invitation fields must be untouched by a reminder resend
        self.assertEqual(request.invitation_email_status, 'pending')
