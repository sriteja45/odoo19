from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manufacturer_id = fields.Many2one('mouser.manufacturer', string='Manufacturer', index=True)
