from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    feedback_request_count = fields.Integer(string='Feedback Requests', compute='_compute_feedback_stats')
    feedback_sent = fields.Boolean(string='Feedback Sent', compute='_compute_feedback_stats')
    last_feedback_date = fields.Datetime(string='Last Feedback Date', compute='_compute_feedback_stats')
    review_completion_status = fields.Selection([
        ('none', 'No Feedback Requested'),
        ('partial', 'Partially Reviewed'),
        ('complete', 'All Reviewed'),
    ], string='Review Completion', compute='_compute_feedback_stats')

    def _compute_feedback_stats(self):
        """Uses _read_group (not the deprecated read_group) so this KEEP
        feature (sale-order review-completion tracking - no native Odoo
        equivalent, see doc/PHASE2_NATIVE_MAPPING.md) stays on the same
        aggregate API as the rest of the module (dashboard, res.partner)."""
        Request = self.env['feedback.request']
        order_ids = self.ids
        if not order_ids:
            return

        stats = {oid: {'count': 0, 'submitted': 0, 'last': False, 'sent': 0} for oid in order_ids}

        for order, status, count, last_delivery in Request._read_group(
                [('sale_order_id', 'in', order_ids)],
                groupby=['sale_order_id', 'status'],
                aggregates=['id:count', 'delivery_date:max']):
            if not order:
                continue
            item = stats[order.id]
            item['count'] += count
            if status == 'submitted':
                item['submitted'] += count
            if last_delivery and (not item['last'] or last_delivery > item['last']):
                item['last'] = last_delivery

        for order, count in Request._read_group(
                [('sale_order_id', 'in', order_ids), ('email_sent', '=', True)],
                groupby=['sale_order_id'],
                aggregates=['id:count']):
            if order and order.id in stats:
                stats[order.id]['sent'] = count

        for order in self:
            item = stats[order.id]
            count = item['count']
            submitted = item['submitted']
            order.feedback_request_count = count
            order.feedback_sent = bool(item.get('sent', 0))
            order.last_feedback_date = item['last']
            if not count:
                order.review_completion_status = 'none'
            elif submitted == count:
                order.review_completion_status = 'complete'
            elif submitted:
                order.review_completion_status = 'partial'
            else:
                order.review_completion_status = 'none'

    def action_view_feedback_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Feedback Requests',
            'res_model': 'feedback.request',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
        }
