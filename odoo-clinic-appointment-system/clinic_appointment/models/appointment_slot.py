from odoo import models, fields, api


class ClinicAppointmentSlot(models.Model):
    _name = 'clinic.appointment.slot'
    _description = 'Clinic Appointment Slot'
    _order = 'slot_date asc, start_time asc'

    name = fields.Char(string="Slot", compute='_compute_name', store=True)
    doctor_id = fields.Many2one('clinic.employee', string="Doctor", required=True, ondelete='cascade')
    slot_date = fields.Date(string="Date", required=True)
    start_time = fields.Float(string="Start Time", required=True)
    end_time = fields.Float(string="End Time", required=True)
    is_booked = fields.Boolean(string="Booked", default=False)
    appointment_id = fields.Many2one('clinic.appointment', string="Appointment", ondelete='set null')

    _sql_constraints = [
        ('unique_doctor_slot_time', 'unique(doctor_id, slot_date, start_time)', 'This slot already exists for this doctor.')
    ]

    @api.depends('start_time', 'end_time')
    def _compute_name(self):
        for rec in self:
            if rec.start_time is not False and rec.end_time is not False:
                rec.name = "%s - %s" % (
                    rec._float_to_time_str(rec.start_time),
                    rec._float_to_time_str(rec.end_time),
                )
            else:
                rec.name = False

    @api.model
    def _float_to_time_str(self, value):
        hours = int(value)
        minutes = int(round((value - hours) * 60))

        if minutes == 60:
            hours += 1
            minutes = 0

        hours = hours % 24
        suffix = 'AM' if hours < 12 else 'PM'
        display_hour = hours if 1 <= hours <= 12 else (hours - 12 if hours > 12 else 12)

        return f"{display_hour:02d}:{minutes:02d} {suffix}"

    @api.model
    def _normalize_float_time(self, value):
        hours = int(value)
        minutes = int(round((value - hours) * 60))

        if minutes == 60:
            hours += 1
            minutes = 0

        return hours + (minutes / 60.0)

    @api.model
    def generate_slots(self, doctor, slot_date):
        if not doctor or not slot_date:
            return False

        if doctor.role != 'doctor' or doctor.available_from is False or doctor.available_to is False:
            return False

        start = self._normalize_float_time(doctor.available_from)
        end = self._normalize_float_time(doctor.available_to)

        if end <= start:
            return False

        existing_slots = self.search([
            ('doctor_id', '=', doctor.id),
            ('slot_date', '=', slot_date),
        ])

        existing_start_times = set(existing_slots.mapped('start_time'))

        current = start
        while round(current + 0.5, 2) <= end:
            next_time = round(current + 0.5, 2)

            if current not in existing_start_times:
                self.create({
                    'doctor_id': doctor.id,
                    'slot_date': slot_date,
                    'start_time': current,
                    'end_time': next_time,
                    'is_booked': False,
                })

            current = next_time

        return True