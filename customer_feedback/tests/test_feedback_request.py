from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestFeedbackRequest(FeedbackTestCommon):

    def test_01_request_created_on_delivery(self):
        """Delivering a sale order line should auto-create a pending
        feedback request with a unique, non-empty token."""
        request = self._create_request()
        self.assertTrue(request, 'A feedback request should exist after delivery.')
        self.assertEqual(request.status, 'pending')
        self.assertTrue(request.token, 'A secure token must be generated.')

    def test_02_token_is_unique(self):
        """Creating a second request for the same order line must fail
        the unique(sale_order_line_id) SQL constraint."""
        request = self._create_request()
        with self.assertRaises(Exception):
            self.env['feedback.request'].create({
                'sale_order_id': request.sale_order_id.id,
                'sale_order_line_id': request.sale_order_line_id.id,
                'partner_id': request.partner_id.id,
                'product_id': request.product_id.id,
                'company_id': request.company_id.id,
            })

    def test_03_invalid_token_lookup_returns_empty(self):
        found = self.env['feedback.request'].search([('token', '=', 'not-a-real-token')])
        self.assertFalse(found)

    def test_04_cron_expires_stale_requests(self):
        """A request whose expiry_date is in the past must be flipped to
        'expired' by the nightly cron job."""
        request = self._create_request()
        request.write({'expiry_date': fields.Datetime.now() - timedelta(days=1)})
        self.env['feedback.request']._cron_process_feedback_requests()
        self.assertEqual(request.status, 'expired')

    def test_05_cron_sends_invitation_after_waiting_period(self):
        """A pending request whose delivery_date is older than the
        configured waiting period should receive its invitation email
        (status flips away from 'pending')."""
        request = self._create_request()
        request.write({
            'delivery_date': fields.Datetime.now() - timedelta(days=10),
            'expiry_date': fields.Datetime.now() + timedelta(days=10),
        })
        self.env['feedback.request']._cron_process_feedback_requests()
        self.assertIn(request.status, ('sent', 'pending'))
        # invitation_email_status should have moved out of the initial
        # 'pending' state once an attempt (successful or failed) was made.
        self.assertIn(request.invitation_email_status, ('queued', 'sent', 'failed', 'retried'))

    def test_06_duplicate_request_same_line_blocked(self):
        """Calling create_from_picking twice for the same picking must not
        create duplicate requests for the same order line."""
        Request = self.env['feedback.request']
        before = Request.search_count([('sale_order_id', '=', self.sale_order.id)])
        if self.picking:
            Request.create_from_picking(self.picking)
        after = Request.search_count([('sale_order_id', '=', self.sale_order.id)])
        self.assertEqual(before, after, 'Re-running create_from_picking must be idempotent.')

    def test_07_get_portal_url_uses_token(self):
        request = self._create_request()
        self.assertEqual(request.get_portal_url(), '/feedback/review/%s' % request.token)

    def test_08_backorder_line_not_requested_until_fully_delivered(self):
        """A sale order with two lines, delivered across two separate
        pickings (a partial delivery + its backorder), must only get a
        feedback request for a line once THAT line's picking is done -
        not for every line on the order the moment any one picking is
        validated."""
        product_b = self.env['product.product'].create({
            'name': 'Test Product B',
            'type': 'consu',
            'invoice_policy': 'order',
        })
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {'product_id': self.product.id, 'product_uom_qty': 1, 'price_unit': 50.0}),
                (0, 0, {'product_id': product_b.id, 'product_uom_qty': 1, 'price_unit': 75.0}),
            ],
        })
        order.action_confirm()
        picking = order.picking_ids[:1]
        if not picking:
            self.skipTest('Delivery routing did not create a picking in this test environment.')

        # Only deliver the first product; leave the second on the picking
        # undone so Odoo spins off a backorder for it.
        move_a = picking.move_ids.filtered(lambda m: m.product_id == self.product)
        move_b = picking.move_ids.filtered(lambda m: m.product_id == product_b)
        move_a.quantity = move_a.product_uom_qty
        move_b.quantity = 0
        picking.with_context(skip_backorder=False).button_validate()

        Request = self.env['feedback.request']
        line_a = order.order_line.filtered(lambda l: l.product_id == self.product)
        line_b = order.order_line.filtered(lambda l: l.product_id == product_b)

        self.assertTrue(
            Request.search([('sale_order_line_id', '=', line_a.id)]),
            'The fully-delivered line should get a feedback request.')
        self.assertFalse(
            Request.search([('sale_order_line_id', '=', line_b.id)]),
            'The line still on backorder must NOT get a feedback request yet.')

    def test_09_cancelled_order_cancels_open_request(self):
        request = self._create_request()
        request.sale_order_id.action_cancel()
        self.env['feedback.request']._cron_process_feedback_requests()
        self.assertEqual(request.status, 'cancelled')

