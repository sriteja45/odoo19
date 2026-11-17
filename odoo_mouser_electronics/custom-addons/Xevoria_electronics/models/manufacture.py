from odoo import models, fields

class XevoriaManufacturer(models.Model):
    _name = 'xevoria.manufacturer'
    _description = 'Xevoria Manufacturer'

    name = fields.Char(required=True)
    logo = fields.Image()