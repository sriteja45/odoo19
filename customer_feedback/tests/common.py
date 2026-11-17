from odoo.tests.common import TransactionCase


class FeedbackTestCommon(TransactionCase):
    """Shared fixtures: a confirmed, fully delivered Sale Order so that
    individual test cases can focus on feedback-specific behaviour instead
    of repeating the sale/stock setup boilerplate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test.customer@example.com',
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'invoice_policy': 'order',
        })

        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        cls.sale_order.action_confirm()

        cls.picking = cls.sale_order.picking_ids[:1]
        if cls.picking:
            for move in cls.picking.move_ids:
                move.quantity = move.product_uom_qty
            cls.picking.button_validate()

    def _create_request(self):
        """Return an existing auto-created feedback.request for the test
        order line, creating one manually as a fallback if the delivery
        did not trigger it (e.g. picking not fully set up)."""
        Request = self.env['feedback.request']
        existing = Request.search([('sale_order_id', '=', self.sale_order.id)], limit=1)
        if existing:
            return existing
        line = self.sale_order.order_line[:1]
        return Request.create({
            'sale_order_id': self.sale_order.id,
            'sale_order_line_id': line.id,
            'partner_id': self.customer.id,
            'product_id': self.product.id,
            'company_id': self.sale_order.company_id.id,
        })
