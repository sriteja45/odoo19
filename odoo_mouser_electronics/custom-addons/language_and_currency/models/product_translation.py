# -*- coding: utf-8 -*-

from odoo import models, fields


class XevoriaProductTranslation(models.Model):
    _name = "xevoria.product.translation"
    _description = "Xevoria Product Translation"
    _rec_name = "translated_name"

    product_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    lang = fields.Char(
        string="Language Code",
        required=True,
        index=True,
        help="Example: hi, hi_IN, te, te_IN, fr, fr_FR",
    )
    source_name = fields.Char(
        string="Original Product Name",
        readonly=True,
    )
    translated_name = fields.Char(
        string="Translated Product Name",
        required=True,
    )
    source_description = fields.Html(
        string="Original Description",
        readonly=True,
    )
    translated_description = fields.Html(
        string="Translated Description",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "product_lang_unique",
            "unique(product_id, lang)",
            "A translation already exists for this product and language.",
        )
    ]
