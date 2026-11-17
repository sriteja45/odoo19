# models/doctor_availability.py
from odoo import models, fields, api
from datetime import datetime, timedelta

class DoctorAvailability(models.Model):
    _name = 'clinic.doctor.availability'
    _description = 'Doctor Availability & Slots'
    
    doctor_id = fields.Many2one('clinic.employee', required=True)
    date = fields.Date(string="Date", required=True)
    slot_start = fields.Float(string="Start Time", required=True)  # 9.0 = 9:00 AM
    slot_end = fields.Float(string="End Time", required=True)       # 9.5 = 9:30 AM
    is_booked = fields.Boolean(default=False)
    appointment_id = fields.Many2one('clinic.appointment')
    is_online = fields.Boolean(string="Online Consultation", default=False)
    
    @api.model
    def generate_slots_for_doctor(self, doctor_id, date):
        """Generate 30-minute slots for a doctor on a given date"""
        doctor = self.env['clinic.employee'].browse(doctor_id)
        start = doctor.available_from  # e.g., 9.0
        end = doctor.available_to       # e.g., 18.0
        
        existing_slots = self.search([
            ('doctor_id', '=', doctor_id),
            ('date', '=', date)
        ])
        existing_times = existing_slots.mapped('slot_start')
        
        current = start
        slots_created = []
        while current < end:
            if current not in existing_times:
                slot = self.create({
                    'doctor_id': doctor_id,
                    'date': date,
                    'slot_start': current,
                    'slot_end': current + 0.5,
                    'is_booked': False
                })
                slots_created.append(slot)
            current += 0.5
        return slots_created
    
    def get_available_slots(self, doctor_id, date):
        """Get only available (not booked) slots"""
        return self.search([
            ('doctor_id', '=', doctor_id),
            ('date', '=', date),
            ('is_booked', '=', False)
        ])