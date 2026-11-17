from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import re


class ClinicPatient(models.Model):
    _name = 'clinic.patient'
    _description = 'Clinic Patient'
    _order = 'id desc'

    patient_id = fields.Char(
        string="Patient ID",
        copy=False,
        readonly=True,
        default="New"
    )

    name = fields.Char(string="Patient Name", required=True)
    birth_date = fields.Date(string="Birth Date", required=True)

    age = fields.Char(
        string="Age",
        compute="_compute_age",
        store=True
    )

    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone", required=True)

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string="Gender")

    appointment_ids = fields.One2many(
        'clinic.appointment',
        'patient_id',
        string="Appointments"
    )

    appointment_count = fields.Integer(
        string="Appointment Count",
        compute="_compute_appointment_count"
    )

    _sql_constraints = [
        ('unique_patient_phone_name', 'unique(phone, name)', 'A patient with this phone and name already exists.'),
        ('unique_patient_code', 'unique(patient_id)', 'Patient ID must be unique.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('patient_id') or vals.get('patient_id') == 'New':
                seq = self.env['ir.sequence'].next_by_code('clinic.patient')
                if not seq:
                    raise ValidationError(
                        "Patient sequence with code 'clinic.patient' is missing. "
                        "Please update sequence.xml and upgrade the module."
                    )
                vals['patient_id'] = seq
        return super().create(vals_list)

    @api.depends('birth_date')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            rec.age = ""
            if rec.birth_date:
                if rec.birth_date > today:
                    rec.age = "Invalid Birth Date"
                    continue

                diff = relativedelta(today, rec.birth_date)
                years = diff.years
                months = diff.months
                days = diff.days

                parts = []
                if years:
                    parts.append(f"{years} {'Year' if years == 1 else 'Years'}")
                if months:
                    parts.append(f"{months} {'Month' if months == 1 else 'Months'}")
                if days:
                    parts.append(f"{days} {'Day' if days == 1 else 'Days'}")

                rec.age = " ".join(parts) if parts else "0 Days"

    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    @api.constrains('birth_date')
    def _check_birth_date(self):
        today = fields.Date.today()
        for rec in self:
            if rec.birth_date and rec.birth_date > today:
                raise ValidationError("Birth date cannot be a future date.")

    @api.constrains('phone')
    def _check_phone(self):
        for rec in self:
            if rec.phone and not rec.phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if rec.phone and len(rec.phone) < 10:
                raise ValidationError("Phone number must be at least 10 digits.")

    @api.constrains('email')
    def _check_email(self):
        for rec in self:
            if rec.email and "@" not in rec.email:
                raise ValidationError("Invalid email address.")

    def action_fix_duplicate_patient_codes(self):
        patients = self.search([], order='id asc')
        seen_codes = set()

        for patient in patients:
            if not patient.patient_id or patient.patient_id in seen_codes:
                new_code = self.env['ir.sequence'].next_by_code('clinic.patient')
                if not new_code:
                    raise ValidationError("Patient sequence not found.")
                patient.write({'patient_id': new_code})
                seen_codes.add(new_code)
            else:
                seen_codes.add(patient.patient_id)

    image_1920 = fields.Image(string="Patient Image")

    image_url = fields.Char(compute="_compute_image_url")
    
    @api.depends('age', 'gender')
    def _compute_image_url(self):
        for rec in self:
            gender = rec.gender or 'male'

            # ✅ extract only numbers (handles "35", "35 years", " 35 ")
            age_value = 0
            if rec.age:
                match = re.search(r'\d+', str(rec.age))
                if match:
                    age_value = int(match.group())

            # 👶 Baby (0–5)
            if age_value <= 5:
                rec.image_url = (
                    '/clinic_appointment/static/description/baby_boy.png'
                    if gender == 'male'
                    else '/clinic_appointment/static/description/baby_girl.png'
                )

            # 🧒 Child (6–15)
            elif age_value <= 15:
                rec.image_url = (
                    '/clinic_appointment/static/description/child_male.png'
                    if gender == 'male'
                    else '/clinic_appointment/static/description/child_female.png'
                )

            # 🧑 Adult (16–59)
            elif age_value < 60:
                rec.image_url = (
                    '/clinic_appointment/static/description/adult_male.png'
                    if gender == 'male'
                    else '/clinic_appointment/static/description/adult_female.png'
                )

            # 👴 Senior (60+)
            else:
                rec.image_url = (
                    '/clinic_appointment/static/description/senior_male.png'
                    if gender == 'male'
                    else '/clinic_appointment/static/description/senior_female.png'
                )
