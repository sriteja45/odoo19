import logging
import secrets
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

DEFAULT_MAX_EMAIL_RETRIES = 3


class FeedbackRequest(models.Model):
    _name = 'feedback.request'
    _description = 'Customer Feedback Request'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                        default=lambda self: self.env['ir.sequence'].next_by_code('feedback.request') or 'New')
    token = fields.Char(string='Secure Token', required=True, copy=False, readonly=True, index=True,
                         default=lambda self: secrets.token_urlsafe(24))

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company, index=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True,
                                     ondelete='cascade', index=True)
    # unique(sale_order_line_id) below already creates a DB-level unique
    # index; index=True here is redundant with that constraint and is
    # intentionally omitted (Phase 4 normalization: don't double-index).
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line', ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Delivery', index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)

    # Indexed: both are scanned on every run of the two hourly/6h crons
    # (_cron_process_feedback_requests / _cron_send_reminders) filtering on
    # status + these date thresholds.
    delivery_date = fields.Datetime(string='Delivery Date', index=True)
    expiry_date = fields.Datetime(string='Expiry Date', index=True)

    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Email Sent'),
        ('submitted', 'Review Submitted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, index=True)

    email_sent = fields.Boolean(string='Invitation Sent', default=False)
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)
    invitation_sent_date = fields.Datetime(string='Invitation Sent On', copy=False, index=True)

    invitation_email_status = fields.Selection([
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
    ], string='Invitation Email Status', default='pending', required=True, copy=False)
    invitation_retry_count = fields.Integer(string='Invitation Retry Count', default=0, copy=False)
    invitation_mail_id = fields.Many2one('mail.mail', string='Invitation Mail', copy=False, readonly=True, ondelete='set null')

    reminder_email_status = fields.Selection([
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
    ], string='Reminder Email Status', default='pending', required=True, copy=False)
    reminder_retry_count = fields.Integer(string='Reminder Retry Count', default=0, copy=False)
    reminder_mail_id = fields.Many2one('mail.mail', string='Reminder Mail', copy=False, readonly=True, ondelete='set null')

    # A feedback request has at most one review (feedback.review carries a
    # unique(request_id) DB constraint). The actual FK/inverse pair is a
    # real One2many, but exposing that as a scalar-looking field misleads
    # every caller that reads it as a single record (controllers, views,
    # tests). Model the collection honestly (review_ids) and derive a real
    # Many2one (review_id) from it so the ORM's own typing communicates the
    # one-request-to-one-review rule instead of relying only on the SQL
    # constraint on the other side.
    review_ids = fields.One2many('feedback.review', 'request_id', string='Reviews')
    review_id = fields.Many2one('feedback.review', string='Review',
                                 compute='_compute_review_id', store=True)

    _token_unique = models.Constraint(
        'unique(token)',
        'The secure token must be unique.',
    )
    _one_request_per_line = models.Constraint(
        'unique(sale_order_line_id)',
        'A feedback request already exists for this order line.',
    )

    @api.model
    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute(
            'CREATE INDEX IF NOT EXISTS feedback_request_status_delivery_idx '
            'ON feedback_request (status, delivery_date)')
        self.env.cr.execute(
            'CREATE INDEX IF NOT EXISTS feedback_request_status_expiry_idx '
            'ON feedback_request (status, expiry_date)')
        self.env.cr.execute(
            'CREATE INDEX IF NOT EXISTS feedback_request_order_line_idx '
            'ON feedback_request (sale_order_id, sale_order_line_id)')
        return res

    @api.depends('review_ids')
    def _compute_review_id(self):
        for request in self:
            # unique(request_id) on feedback.review guarantees at most one
            # record here; [:1] is defensive, not "pick the first of many".
            request.review_id = request.review_ids[:1]

    @api.model
    def _get_waiting_days(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.waiting_days', default=3))

    @api.model
    def _get_expiry_days(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.expiry_days', default=15))

    @api.model
    def _get_reminder_days(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.reminder_days', default=4))

    @api.model
    def _get_max_email_retries(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.max_email_retries', default=DEFAULT_MAX_EMAIL_RETRIES))

    @api.model
    def _get_admin_notification_email(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.admin_notification_email') or self.env.company.email

    @api.model
    def _cron_batch_size(self):
        return max(50, min(int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.cron_batch_size', default=200)), 1000))

    @api.model
    def create_from_picking(self, picking):
        """Create feedback requests for all eligible lines of a delivered picking."""
        requests = self.env['feedback.request']
        sale_order = picking.sale_id
        if not sale_order or sale_order.state == 'cancel':
            return requests

        # Only products actually moved (and completed) on *this* picking are
        # candidates - a sale order can ship across several deliveries/backorders,
        # and lines not covered by this picking must not be touched here.
        delivered_product_ids = set(
            picking.move_ids.filtered(lambda m: m.state == 'done').mapped('product_id').ids
        )
        if not delivered_product_ids:
            return requests

        eligible_lines = sale_order.order_line.filtered(lambda line: (
            not line.display_type and
            line.product_id.type != 'service' and
            line.product_id.id in delivered_product_ids and
            line.product_id.active and
            (not line.product_uom_qty or line.qty_delivered + 1e-6 >= line.product_uom_qty)
        ))
        if not eligible_lines:
            return requests

        existing_lines = self.search([
            ('sale_order_line_id', 'in', eligible_lines.ids),
        ]).mapped('sale_order_line_id').ids
        new_lines = eligible_lines.filtered(lambda line: line.id not in existing_lines)
        if not new_lines:
            return requests

        expiry_days = self._get_expiry_days()
        now = fields.Datetime.now()
        vals_list = [{
            'sale_order_id': sale_order.id,
            'sale_order_line_id': line.id,
            'picking_id': picking.id,
            'partner_id': sale_order.partner_id.id,
            'product_id': line.product_id.id,
            'company_id': sale_order.company_id.id,
            'delivery_date': picking.date_done or now,
            'expiry_date': now + timedelta(days=expiry_days),
        } for line in new_lines]
        try:
            with self.env.cr.savepoint():
                requests = self.create(vals_list)
        except IntegrityError:
            # Another delivery worker may have won the unique order-line race.
            requests = self.search([('sale_order_line_id', 'in', new_lines.ids)])
        return requests

    def _send_templated_email(self, template_xmlid, status_field, retry_field,
                               sent_date_field=None, flag_field=None, mail_field=None,
                               force_send=False):
        """Generic helper that sends a mail.template to each record in self and
        tracks the outcome (Pending / Queued / Sent / Failed / Retried).

        - force_send=False (cron / bulk): enqueue via Odoo mail queue; status -> 'queued'.
        - force_send=True  (manual UI button): attempt immediate SMTP send; status -> 'sent'
          when the mail.mail ends up sent, else 'queued' / 'failed'.
        - On render/send exception: retry_count increments, status -> 'failed'. Once
          max retries is reached, the administrator is notified.
        """
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning('Customer Feedback: mail template %s not found.', template_xmlid)
            return

        max_retries = self._get_max_email_retries()

        for request in self:
            if request[status_field] == 'failed' and request[retry_field] >= max_retries:
                # Retries exhausted; admin already notified. Skip until manual action.
                continue

            was_failed = request[status_field] == 'failed'
            try:
                # Cron/bulk: queue only. Manual UI actions may force_send so the
                # operator sees an immediate result during testing/support.
                mail_id = template.send_mail(
                    request.id, force_send=force_send, raise_exception=True)
            except Exception:
                _logger.exception(
                    'Customer Feedback: failed to send email (%s) for request %s',
                    status_field, request.name)
                retry_count = request[retry_field] + 1
                request.write({
                    retry_field: retry_count,
                    status_field: 'failed',
                })
                if retry_count >= max_retries:
                    request._notify_admin_email_failure(status_field, retry_count)
                continue

            # Determine post-send status from the mail.mail record when possible.
            # IMPORTANT: with force_send=True, Odoo often deletes the mail.mail
            # row immediately after a successful SMTP send. Storing that id on
            # invitation_mail_id / reminder_mail_id would then violate the FK.
            # Only store the FK when the row still exists.
            email_status = 'queued'
            mail = self.env['mail.mail'].browse(mail_id).exists() if mail_id else self.env['mail.mail']
            if mail:
                if mail.state == 'sent':
                    email_status = 'retried' if was_failed else 'sent'
                elif mail.state == 'exception':
                    email_status = 'failed'
                elif mail.state == 'outgoing':
                    email_status = 'queued'
                elif force_send:
                    email_status = 'retried' if was_failed else 'sent'
            elif force_send and mail_id:
                # Mail id was returned, then the row was auto-deleted after a
                # successful send → treat as delivered.
                email_status = 'retried' if was_failed else 'sent'
            elif force_send:
                email_status = 'retried' if was_failed else 'sent'

            vals = {status_field: email_status}
            if mail_field and mail:
                # Only link when the mail.mail row still exists (avoids FK error
                # after Odoo auto-deletes sent mails).
                vals[mail_field] = mail.id
            if flag_field:
                vals[flag_field] = True
            if sent_date_field:
                vals[sent_date_field] = fields.Datetime.now()
            request.write(vals)

    def _notify_admin_email_failure(self, status_field, retry_count):
        """Optional administrator notification once retries are exhausted.
        Logs the failure and, if an admin/company email is configured, sends a
        short notice. The feedback request itself is left untouched so it stays
        available for manual follow-up."""
        self.ensure_one()
        _logger.error(
            'Customer Feedback: giving up on %s for request %s after %s attempts.',
            status_field, self.name, retry_count)

        admin_email = self._get_admin_notification_email()
        if not admin_email:
            return
        try:
            self.env['mail.mail'].sudo().create({
                'subject': _('Customer Feedback: email delivery failed for %s') % self.name,
                'email_to': admin_email,
                'body_html': _(
                    '<p>The %(field)s could not be delivered after %(count)s attempts '
                    'for feedback request <b>%(name)s</b> (customer: %(partner)s, '
                    'product: %(product)s).</p>'
                    '<p>The request has been left active so it can be handled manually.</p>'
                ) % {
                    'field': status_field.replace('_', ' '),
                    'count': retry_count,
                    'name': self.name,
                    'partner': self.partner_id.name,
                    'product': self.product_id.display_name,
                },
            }).send()
        except Exception:
            _logger.exception('Customer Feedback: failed to notify administrator of email failure.')

    def action_send_invitation(self):
        """Send the feedback invitation email (manual UI → force_send for immediate delivery)."""
        to_send = self.filtered(lambda r: r.status == 'pending')
        # Manual button: force_send so the operator gets immediate SMTP attempt
        # instead of leaving mail stuck in Outgoing until the queue cron runs.
        to_send._send_templated_email(
            'customer_feedback.mail_template_feedback_invitation',
            status_field='invitation_email_status',
            retry_field='invitation_retry_count',
            sent_date_field='invitation_sent_date',
            flag_field='email_sent',
            mail_field='invitation_mail_id',
            force_send=True,
        )
        to_send.filtered(
            lambda r: r.invitation_email_status in ('queued', 'sent', 'retried')
        ).write({'status': 'sent'})

    def action_send_reminder(self):
        """Send the reminder email (manual UI → force_send for immediate delivery).

        Guards against a double-click (or two concurrent callers) re-sending
        a reminder that already went out: the form button hides itself once
        reminder_sent is True, but that's a UI-layer courtesy, not a
        guarantee, so the same check is enforced here. reminder_sent is left
        for _send_templated_email to set only once the send outcome is known
        - setting it up front would defeat that method's own failed-send
        retry logic.
        """
        eligible = self.filtered(lambda r: not r.reminder_sent)
        if not eligible:
            return False
        eligible._send_templated_email(
            'customer_feedback.mail_template_feedback_reminder',
            status_field='reminder_email_status',
            retry_field='reminder_retry_count',
            flag_field='reminder_sent',
            mail_field='reminder_mail_id',
            force_send=True,
        )

    @api.model
    def _cron_process_feedback_requests(self):
        """Batch cron for invitations, expiry, cancellation and return reconciliation.

        Bounded batches prevent a large database from turning one cron execution
        into an unbounded transaction. Record creation remains idempotent because
        sale_order_line_id is protected by a database unique constraint.
        """
        now = fields.Datetime.now()
        waiting_days = self._get_waiting_days()
        threshold = now - timedelta(days=waiting_days)
        batch = self._cron_batch_size()

        # FOR UPDATE SKIP LOCKED: ir.cron already serializes ticks of this
        # *same* scheduled job, but a manual "Run Manually" click can still
        # overlap a scheduler tick. Locking the candidate rows here means a
        # second concurrent caller simply skips rows the first has claimed,
        # instead of both reading status='pending' and both sending.
        self.env.cr.execute("""
            SELECT id FROM feedback_request
            WHERE status = 'pending' AND delivery_date <= %s AND expiry_date >= %s
            ORDER BY id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, (threshold, now, batch))
        to_send = self.browse([r[0] for r in self.env.cr.fetchall()])
        to_send.action_send_invitation()

        expired = self.search([
            ('status', 'in', ('pending', 'sent')),
            ('expiry_date', '<', now),
        ], order='id', limit=batch)
        if expired:
            expired.write({'status': 'expired'})

        # A cancelled order or a returned line must not continue to solicit
        # feedback. A partial return is also cancelled once delivered quantity
        # falls below the ordered quantity. Submitted reviews are preserved.
        stale = self.search([
            ('status', 'in', ('pending', 'sent')),
            ('sale_order_id.state', '=', 'cancel'),
        ], order='id', limit=batch)
        if stale:
            stale.write({'status': 'cancelled'})

        returned = self.search([
            ('status', 'in', ('pending', 'sent')),
            ('sale_order_line_id', '!=', False),
        ], order='id', limit=batch)
        returned = returned.filtered(lambda r: (
            r.sale_order_line_id.qty_delivered <= 1e-6 or
            (r.sale_order_line_id.product_uom_qty and
             r.sale_order_line_id.qty_delivered + 1e-6 < r.sale_order_line_id.product_uom_qty)
        ))
        if returned:
            returned.write({'status': 'cancelled'})

    @api.model
    def _cron_send_reminders(self):
        """Queue reminders in bounded batches; native mail queue handles SMTP retries."""
        reminder_days = self._get_reminder_days()
        threshold = fields.Datetime.now() - timedelta(days=reminder_days)
        to_remind = self.search([
            ('status', '=', 'sent'),
            ('invitation_email_status', 'in', ('queued', 'sent', 'retried')),
            ('reminder_sent', '=', False),
            ('invitation_sent_date', '!=', False),
            ('invitation_sent_date', '<=', threshold),
            ('expiry_date', '>=', fields.Datetime.now()),
        ], order='id', limit=self._cron_batch_size())
        to_remind.action_send_reminder()

    def get_portal_url(self):
        self.ensure_one()
        return '/feedback/review/%s' % self.token

    def action_view_review(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Review',
            'res_model': 'feedback.review',
            'view_mode': 'form',
            'res_id': self.review_id.id,
        }
