from odoo import models, fields

class ClinicDisease(models.Model):
    _name = 'clinic.disease'
    _description = 'Disease Master'

    name = fields.Char(
        string="Disease Name",
        required=True
    )

    icd_code = fields.Char(
        string="ICD Code"
    )

    