from odoo import models, fields

class ClinicSpecialization(models.Model):
    _name = 'clinic.specialization'
    _description = 'Doctor Specialization'

    name = fields.Char(required=True)
