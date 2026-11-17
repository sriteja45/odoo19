# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    """ EXTENSION of sale.order. Adds a manual trigger for the same
    review-request mechanism the automated cron uses (see
    sale_order_line.py). No existing sale.order field, method or view
    section is modified - only additive fields + one button, wired into
    the existing form view via view inheritance (views/sale_order_views.xml).
    """
    _inherit = 'sale.order'

    review_request_count = fields.Integer(
        string="Review Requests Sent",
        compute='_compute_review_request_count',
    )

    def _compute_review_request_count(self):
        for order in self:
            order.review_request_count = len(
                order.order_line.filtered('review_requested')
            )

    def action_send_review_request(self):
        """Manually (re)send the 'rate your purchase' email for every
        eligible line on this order, reusing the exact same helper the
        cron job calls - no duplicate email-sending logic."""
        self.ensure_one()
        eligible_lines = self.order_line.filtered(
            lambda line: line.product_id and not line.display_type
        )
        eligible_lines._send_review_request_email(force=True)
        return True
