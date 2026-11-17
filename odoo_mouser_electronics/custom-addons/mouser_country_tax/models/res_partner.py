from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    country_tax_type = fields.Selection([
        ('india', 'India GST'),
        ('usa', 'USA Sales Tax'),
        ('china', 'China VAT'),
        ('russia', 'Russia VAT'),
    ], string="Country Tax Type")