from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_apply_combo_offer(self):

        offers = self.env["combo.offer"].search([
            ("active", "=", True)
        ])

        for order in self:

            for line in order.order_line:

                for offer in offers:

                    if line.product_id in offer.product_ids:

                        if line.product_uom_qty >= offer.minimum_qty:

                            if offer.offer_type == "percentage":

                                line.discount = offer.discount

                            elif offer.offer_type == "fixed":

                                unit = line.price_unit

                                line.price_unit = (
                                    unit -
                                    offer.discount
                                )

                            elif offer.offer_type == "combo":

                                line.price_unit = (
                                    offer.combo_price /
                                    line.product_uom_qty
                                )