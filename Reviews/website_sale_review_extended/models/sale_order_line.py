# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    """ EXTENSION of sale.order.line.

    Odoo core sends no post-purchase "please review this product" email at
    all. Rather than writing a standalone mailer, we reuse the standard
    ir.cron + mail.template infrastructure and hang two small tracking
    fields off the existing sale order line (the natural place to know
    "was this specific product, on this specific order, delivered, and
    have we already asked about it").
    """
    _inherit = 'sale.order.line'

    review_requested = fields.Boolean(
        string="Review Requested", default=False, copy=False,
        help="True once a 'rate your purchase' email has been sent for "
             "this order line.",
    )
    review_requested_date = fields.Datetime(
        string="Review Requested On", copy=False, readonly=True,
    )

    @api.model
    def _cron_send_review_requests(self):
        """Called by the ir.cron record in data/ir_cron_data.xml."""
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param('website_sale_review_extended.auto_request_enabled', 'False') != 'True':
            return
        delay_days = int(params.get_param('website_sale_review_extended.request_delay_days', '7') or 7)
        deadline = fields.Datetime.now() - timedelta(days=delay_days)

        lines = self.search([
            ('review_requested', '=', False),
            ('order_id.state', '=', 'sale'),
            ('qty_delivered', '>', 0),
            ('product_id', '!=', False),
            ('display_type', '=', False),
            ('order_id.date_order', '<=', deadline),
        ])
        lines._send_review_request_email()

    def _send_review_request_email(self, force=False):
        """Send (or resend, if force=True) the review-request email for
        each eligible line, one email per order (grouping lines) so a
        customer who bought 3 products gets a single email, not three.
        """
        template = self.env.ref(
            'website_sale_review_extended.mail_template_review_request',
            raise_if_not_found=False,
        )
        if not template:
            return

        lines = self.filtered(lambda l: l.product_id and not l.display_type)
        if not force:
            lines = lines.filtered(lambda l: not l.review_requested)

        orders = lines.mapped('order_id')
        for order in orders:
            order_lines = lines.filtered(lambda l: l.order_id == order)
            if not order.partner_id.email:
                continue
            template.send_mail(order.id, force_send=False, email_layout_xmlid='mail.mail_notification_light')
            order_lines.write({
                'review_requested': True,
                'review_requested_date': fields.Datetime.now(),
            })
