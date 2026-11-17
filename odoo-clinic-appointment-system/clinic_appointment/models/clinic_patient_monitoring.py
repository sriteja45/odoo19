from odoo import models, fields


class ClinicPatientMonitoring(models.Model):
    _name = 'clinic.patient.monitoring'
    _description = 'Patient Monitoring'
    _order = 'monitor_time desc'

    appointment_id = fields.Many2one(
        'clinic.appointment',
        string="Appointment",
        required=True,store=True
    )

    patient_name = fields.Char(
        related='appointment_id.patient_name',
        string="Patient",
        store=True,
        readonly=True
    )

    room_id = fields.Many2one(
        'hospital.room',
        string="Room"
    )

    temperature = fields.Float(string="Temperature")
    blood_pressure = fields.Char(string="Blood Pressure")
    pulse_rate = fields.Integer(string="Pulse Rate")
    oxygen = fields.Float(string="Oxygen %")

    notes = fields.Text(string="Nurse Notes")

    monitor_time = fields.Datetime(
        string="Monitoring Time",
        default=fields.Datetime.now,
        readonly=True
    )

    nurse_id = fields.Many2one(
        'res.users',
        string="Monitored By",
        default=lambda self: self.env.user,
        readonly=True
    )