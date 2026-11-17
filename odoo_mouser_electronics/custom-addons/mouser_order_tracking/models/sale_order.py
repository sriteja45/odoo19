from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ==========================
    # Shipment Details
    # ==========================

    tracking_number = fields.Char(
        string="Tracking Number",
        default="TRK123456789"
    )

    courier_name = fields.Char(
        string="Courier",
        default="BlueDart"
    )

    shipping_method = fields.Char(
        string="Shipping Method",
        default="Standard Delivery"
    )

    payment_method = fields.Char(
        string="Payment Method",
        default="Credit Card"
    )

    current_location = fields.Char(
        string="Current Location",
        default="Hyderabad Hub"
    )

    estimated_delivery = fields.Datetime(
        string="Estimated Delivery"
    )

    # ==========================
    # Shipment Status
    # ==========================

    shipment_status = fields.Selection([
        ("confirmed", "Order Confirmed"),
        ("packed", "Packed"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
    ],
        string="Shipment Status",
        default="confirmed"
    )

    # ==========================
    # Timeline Dates
    # ==========================

    confirmed_date = fields.Datetime(
        string="Confirmed Time"
    )

    packed_date = fields.Datetime(
        string="Packed Time"
    )

    shipped_date = fields.Datetime(
        string="Shipped Time"
    )

    out_delivery_date = fields.Datetime(
        string="Out For Delivery Time"
    )

    delivered_date = fields.Datetime(
        string="Delivered Time"
    )

    # ==========================
    # Customer Requests
    # ==========================

    cancel_requested = fields.Boolean(
        string="Cancel Requested",
        default=False
    )

    return_requested = fields.Boolean(
        string="Return Requested",
        default=False
    )

    # ==========================
    # Buttons
    # ==========================

    def action_confirmed(self):
        for order in self:
            order.write({
                "shipment_status": "confirmed",
                "confirmed_date": fields.Datetime.now(),
            })

    def action_packed(self):
        for order in self:
            order.write({
                "shipment_status": "packed",
                "packed_date": fields.Datetime.now(),
            })

    def action_shipped(self):
        for order in self:
            order.write({
                "shipment_status": "shipped",
                "shipped_date": fields.Datetime.now(),
            })

    def action_out_for_delivery(self):
        for order in self:
            order.write({
                "shipment_status": "out_for_delivery",
                "out_delivery_date": fields.Datetime.now(),
            })

    def action_delivered(self):
        for order in self:
            order.write({
                "shipment_status": "delivered",
                "delivered_date": fields.Datetime.now(),
            })

    def action_request_cancel(self):
        for order in self:
            order.cancel_requested = True

    def action_request_return(self):
        for order in self:
            order.return_requested = True