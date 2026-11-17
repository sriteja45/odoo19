from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class HospitalRoomBooking(models.Model):
    _name = 'hospital.room.booking'
    _description = 'Room Booking'
    _rec_name = 'patient_id'

    patient_id = fields.Many2one(
        'clinic.patient',
        string="Patient",
        required=True,
    )

    room_id = fields.Many2one(
        'hospital.room',
        string="Room",
        required=True,
        domain=[('status', '=', 'available')]
    )

    doctor_id = fields.Many2one(
        'clinic.employee',
        string="Doctor",
        domain=[('role', '=', 'doctor')],
        ondelete='set null'
    )

    check_in = fields.Datetime(string="Check In", required=True)
    check_out = fields.Datetime(string="Check Out")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('booked', 'Booked'),
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged'),
        ('done', 'Done'),
    ], string="Status", default='draft')

    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_amount",
        store=True
    )

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_out < rec.check_in:
                raise ValidationError("Check Out must be greater than Check In.")

    @api.constrains('room_id', 'state')
    def _check_room_availability(self):
        for rec in self:
            if rec.room_id and rec.room_id.status != 'available' and rec.state == 'draft':
                raise UserError("Selected room is not available.")

    @api.depends('check_in', 'check_out', 'room_id')
    def _compute_amount(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.room_id:
                duration = rec.check_out - rec.check_in
                days = duration.days
                if days <= 0:
                    days = 1
                rec.total_amount = days * rec.room_id.charges_per_day
            else:
                rec.total_amount = 0.0


    def action_book(self):
        for rec in self:
            if rec.room_id.status != 'available':
                raise UserError("Room is not available.")
            rec.state = 'booked'
            rec.room_id.status = 'booked'

    def action_admit(self):
        for rec in self:
            rec.state = 'admitted'
            rec.room_id.status = 'occupied'

    def action_discharge(self):
        for rec in self:
            rec.state = 'discharged'
            rec.room_id.status = 'cleaning'

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.room_id.status = 'available'