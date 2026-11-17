from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    demo_video_url = fields.Char(
        string="Demo Video URL"
    )