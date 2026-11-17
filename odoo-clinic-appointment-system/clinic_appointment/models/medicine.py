from odoo import models, fields
from odoo.exceptions import UserError


class ClinicMedicine(models.Model):
    _name = 'clinic.medicine'
    _description = 'Clinic Medicine'

    name = fields.Char(string="Medicine Name", required=True)

    category = fields.Selection([
        ('tablet', 'Tablet'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('capsule', 'Capsule'),
        ('ointment', 'Ointment'),
    ], string="Medicine Type")

    