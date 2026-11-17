from odoo import models, fields, api


class ComboOffer(models.Model):
    _name = "combo.offer"
    _description = "Combo Offer"
    _rec_name = "name"

    name = fields.Char(
        string="Offer Name",
        required=True
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    product_ids = fields.Many2many(
        "product.product",
        string="Products"
    )

    offer_type = fields.Selection(
        [
            ("percentage", "Percentage Discount"),
            ("fixed", "Fixed Discount"),
            ("combo", "Combo Price"),
        ],
        string="Offer Type",
        required=True,
        default="percentage"
    )

    minimum_qty = fields.Integer(
        string="Minimum Quantity",
        default=1,
        required=True
    )

    discount = fields.Float(
        string="Discount",
        default=0
    )

    combo_price = fields.Float(
        string="Combo Price",
        default=0
    )

    final_price = fields.Float(
        string="Final Price",
        compute="_compute_final_price",
        store=False
    )

    @api.depends("combo_price", "discount", "offer_type")
    def _compute_final_price(self):

        for rec in self:

            if rec.offer_type == "combo":

                rec.final_price = (
                    rec.combo_price
                    -
                    (
                        rec.combo_price
                        * rec.discount
                        / 100
                    )
                )

            else:

                rec.final_price = 0