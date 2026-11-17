from odoo import models, fields

class HospitalBed(models.Model):
    _name = 'hospital.bed'
    _description = 'Hospital Bed'

    name = fields.Char(string="Bed Number", required=True)

    room_id = fields.Many2one(
        'hospital.room',
        string="Room",
        required=True
    )

    bed_ids = fields.One2many(
    'hospital.bed',
    'room_id',
    string="Beds"
)


    status = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning')
    ], default='available')