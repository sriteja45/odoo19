from odoo import models, fields


class ClinicPrescription(models.Model):
    _name = 'clinic.prescription'
    _description = 'Patient Prescription'

    patient_name = fields.Char(
        string="Patient Name",
        required=True
    )

    doctor_id = fields.Many2one(
        'clinic.employee', role='doctor',
        string="Doctor"
    )

    date = fields.Date(
        string="Prescription Date"
    )

    medicine_ids = fields.Many2many(
        'clinic.medicine',
        string="Medicines"
    )

    dosage = fields.Text(
        string="Dosage Instructions"
    )

    notes = fields.Text(
        string="Doctor Notes"
    )