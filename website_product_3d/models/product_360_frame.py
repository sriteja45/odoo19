# -*- coding: utf-8 -*-

from odoo import fields, models


class Product360Frame(models.Model):
    _name = "product.360.frame"
    _description = "Product 360° Image Frame"
    _order = "sequence, id"

    name = fields.Char(
        string="Name",
        help="Optional label for this frame (e.g. 'Front', '45°').",
    )
    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    image = fields.Binary(
        string="Image",
        attachment=True,
        required=True,
        help="Upload one photo of the product. Order the frames by sequence "
             "(drag the handle) so the spin looks correct. 24–36 frames "
             "(every 10–15°) give a smooth result.",
    )
    image_filename = fields.Char(string="Filename")
