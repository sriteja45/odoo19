from odoo import http
from odoo.http import request


class MouserOrderTracking(http.Controller):

    # ==========================================
    # My Orders Page
    # ==========================================

    @http.route(
        ['/my/orders'],
        type='http',
        auth='user',
        website=True
    )
    def my_orders(self, **kwargs):

        partner = request.env.user.partner_id

        orders = request.env['sale.order'].sudo().search(
            [('partner_id', '=', partner.id)],
            order='create_date desc'
        )

        return request.render(
            'mouser_order_tracking.my_orders_page',
            {
                'orders': orders,
            }
        )

    # ==========================================
    # Order Details
    # ==========================================

    @http.route(
        ['/my/orders/<int:order_id>'],
        type='http',
        auth='user',
        website=True
    )
    def order_details(self, order_id, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)

        if not order.exists():
            return request.not_found()

        if order.partner_id != request.env.user.partner_id:
            return request.redirect('/my/orders')

        return request.render(
            'mouser_order_tracking.order_details_page',
            {
                'order': order,
            }
        )

    # ==========================================
    # Track Order
    # ==========================================

    @http.route(
        ['/my/orders/<int:order_id>/track'],
        type='http',
        auth='user',
        website=True
    )
    def track_order(self, order_id, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)

        if not order.exists():
            return request.not_found()

        if order.partner_id != request.env.user.partner_id:
            return request.redirect('/my/orders')

        return request.render(
            'mouser_order_tracking.track_order_page',
            {
                'order': order,
            }
        )

    # ==========================================
    # Cancel Order
    # ==========================================
    @http.route(
        ['/my/orders/<int:order_id>/cancel'],
        type='http',
        auth='user',
        website=True
        )
    def cancel_order(self, order_id, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)

        if order.exists():

            order.write({
                'state': 'cancel'
            })

        return request.redirect('/my/orders/%s' % order.id)

    # ==========================================
    # Return Order
    # ==========================================

    @http.route(
        ['/my/orders/<int:order_id>/return'],
        type='http',
        auth='user',
        website=True
    )
    def return_order(self, order_id, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)

        if order.exists():

            order.write({
                'return_requested': True
            })

        return request.redirect('/my/orders/%s' % order.id)