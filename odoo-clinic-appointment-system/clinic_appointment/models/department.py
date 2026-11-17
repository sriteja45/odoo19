from odoo import models,fields


class ClinicDepartment(models.Model):
    _name = "clinic.department"
    _description = "Clinic Department"

    name = fields.Char(string="Department Name", required=True, unique=True)