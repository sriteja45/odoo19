from odoo import models, fields

class MouserCountryTax(models.Model):
    _name = 'mouser.country.tax'
    _description = 'Country Tax Rules'

    name = fields.Char(string="Tax Name", required=True)
    country_id = fields.Many2one('res.country', string="Country", required=True)
    tax_percent = fields.Float(string="Tax Percentage")
    active = fields.Boolean(default=True)