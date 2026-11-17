from odoo import _, fields, models
from odoo.exceptions import UserError


class FeedbackResendEmailWizard(models.TransientModel):
    """Administrative convenience wizard (SRS Section 18 module structure /
    Section 16 Exception Handling - "Retry Count Exceeded -> Administrator
    Notification") that lets an administrator bulk-resend the invitation or
    reminder email for one or more feedback requests.

    This complements the single-record "Send Invitation Now" / "Send
    Reminder Now" buttons already on the feedback.request form: those only
    work while a request is still in the state the normal flow expects
    (status == 'pending' / 'sent') and don't help once automatic retries
    have been exhausted (invitation_email_status == 'failed' after
    max_email_retries). This wizard can be launched on a multi-record
    selection from the list view, optionally resets the exhausted retry
    counters, and (re)sends regardless of the request's current status -
    skipping only requests where sending would be meaningless (already
    submitted or cancelled).
    """
    _name = 'feedback.resend.email.wizard'
    _description = 'Resend Feedback Email'

    request_ids = fields.Many2many(
        'feedback.request', string='Feedback Requests', required=True,
        default=lambda self: self.env.context.get('active_ids', []))
    email_type = fields.Selection([
        ('invitation', 'Invitation Email'),
        ('reminder', 'Reminder Email'),
    ], string='Email', required=True, default='invitation')
    reset_retry_count = fields.Boolean(
        string='Reset retry count', default=True,
        help='Clear the previous failed-attempt counter so requests that already '
             'exhausted their automatic retries (and were left for manual follow-up) '
             'can be sent again.')

    def _eligible_requests(self):
        """Requests it actually makes sense to (re)send to: not yet
        submitted and not cancelled. Submitted requests already have their
        review; cancelled ones should never receive a feedback email."""
        return self.request_ids.filtered(lambda r: r.status not in ('submitted', 'cancelled'))

    def action_resend(self):
        self.ensure_one()
        requests = self._eligible_requests()
        if not requests:
            raise UserError(_(
                'None of the selected feedback requests are eligible for a %s email '
                '(they have already been submitted or cancelled).'
            ) % dict(self._fields['email_type'].selection).get(self.email_type, self.email_type))

        if self.email_type == 'invitation':
            if self.reset_retry_count:
                requests.write({
                    'invitation_retry_count': 0,
                    'invitation_email_status': 'pending',
                })
            requests._send_templated_email(
                'customer_feedback.mail_template_feedback_invitation',
                status_field='invitation_email_status',
                retry_field='invitation_retry_count',
                sent_date_field='invitation_sent_date',
                flag_field='email_sent',
            )
            requests.filtered(
                lambda r: r.status == 'pending' and r.invitation_email_status in ('sent', 'retried')
            ).write({'status': 'sent'})
        else:
            if self.reset_retry_count:
                requests.write({
                    'reminder_retry_count': 0,
                    'reminder_email_status': 'pending',
                })
            requests._send_templated_email(
                'customer_feedback.mail_template_feedback_reminder',
                status_field='reminder_email_status',
                retry_field='reminder_retry_count',
                flag_field='reminder_sent',
            )

        status_field = 'invitation_email_status' if self.email_type == 'invitation' else 'reminder_email_status'
        sent = requests.filtered(lambda r: r[status_field] in ('sent', 'retried'))
        failed = requests - sent

        message = _('%(sent)s of %(total)s email(s) sent successfully.') % {
            'sent': len(sent), 'total': len(requests),
        }
        if failed:
            message += ' ' + _('%s failed again and will need another manual attempt.') % len(failed)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Resend Email'),
                'message': message,
                'type': 'warning' if failed else 'success',
                'sticky': bool(failed),
            },
        }
