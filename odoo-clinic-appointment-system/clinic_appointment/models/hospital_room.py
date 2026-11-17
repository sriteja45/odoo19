from odoo import models, fields


class HospitalRoom(models.Model):
    _name = 'hospital.room'
    _description = 'Hospital Room'
    _rec_name = 'name'

    name = fields.Char(string="Room Number", required=True)

    room_type = fields.Selection([
        ('general', 'General Ward'),
        ('private', 'Private Room'),
        ('icu', 'ICU'),
    ], string="Room Type", required=True)

    bed_count = fields.Integer(string="Beds", default=1)

    status = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning'),
    ], string="Status", default='available')

    charges_per_day = fields.Float(string="Charges per Day")