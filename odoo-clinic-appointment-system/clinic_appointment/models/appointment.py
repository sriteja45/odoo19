from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools import format_datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class ClinicAppointment(models.Model):
    _name = 'clinic.appointment'
    _order = 'doctor_id, appointment_date'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Clinic Appointment'

    appointment_id = fields.Char(
        string="Appointment ID",
        
        copy=False,
        readonly=True,
        default="New"
    )

    
    token_number = fields.Integer(string="Token No")

    patient_id = fields.Many2one(
        'clinic.patient',
        string="Patient",
        ondelete='restrict',
        tracking=True
    )

    patient_code = fields.Char(
        string="Patient ID",
        related="patient_id.patient_id",
        store=True,
        readonly=True
    )

    

    # ======================
    # Patient Details
    # ======================

    patient_name = fields.Char(required=True)
 
    birth_date = fields.Date( string="Birth Date", required=True)

    age = fields.Char(
        string="Age",
        compute="_compute_age",
        store=True
    )

    email = fields.Char()
    phone = fields.Char()


    # ======================
    # Appointment Details
    # ======================

    specialization_id = fields.Many2one(
        'clinic.specialization',
        required=True
    )

    doctor_id = fields.Many2one(
        'clinic.employee',
        string="Doctor",
        domain=[('role', '=', 'doctor')],
        required=True
    )

    doctor_user_id = fields.Many2one(
        'res.users',
        string="Doctor User",
        related="doctor_id.user_id",
        store=True
    )

    

    appointment_date = fields.Date(required=True, tracking=True)
    slot_id = fields.Many2one(
        'clinic.appointment.slot', 
        string="Time Slot", 
        domain="[('doctor_id', '=', doctor_id), ('slot_date', '=', appointment_date), ('is_booked', '=', False)]",
        required=True, tracking=True
    )
    appointment_time = fields.Char(string="Appointment Time", related="slot_id.name", store=True)

    booking_by = fields.Selection([
        ('customer', 'Customer'),
        ('employee', 'Employee')
    ], string="Booking By", default="employee", required=True, tracking=True)

    cancel_reason = fields.Text(
        string="Cancel Reason"
    )

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string="Gender")

    reason = fields.Selection([
        ('fever', 'Fever'),
        ('cold', 'Cold / Flu'),
        ('cough', 'Cough'),
        ('headache', 'Headache'),
        ('body_pain', 'Body Pain'),
        ('stomach_pain', 'Stomach Pain'),
        ('back_pain', 'Back Pain'),
        ('skin_problem', 'Skin Problem'),
        ('general_checkup', 'General Checkup'),
        ('baby_checkup', 'Baby Checkup'),
        ('follow_up', 'Follow-up Visit'),
        ('injury', 'Injury / Accident'),
        ('other', 'Other'),
    ], string="Reason for Visit")

    other_reason = fields.Text(
        string="Other Symptoms / Reason"
    )

    # ======================
    # Lab Requests
    # ======================

    lab_request_ids = fields.One2many(
        'clinic.lab.request',
        'appointment_id',
        string="Lab Requests"
    )

    
    
    # ======================
    # CREATE / WRITE / DELETE
    # ======================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('appointment_id') or vals.get('appointment_id') == 'New':
                seq = self.env['ir.sequence'].next_by_code('clinic.appointment')
                if not seq:
                    raise ValidationError(
                        "Appointment sequence with code 'clinic.appointment' is missing."
                    )
                vals['appointment_id'] = seq

            phone = vals.get('phone')
            patient_id = vals.get('patient_id')
            patient_name = vals.get('patient_name')

            if patient_id:
                patient = self.env['clinic.patient'].browse(patient_id)
                if patient.exists():
                    vals['patient_name'] = patient.name
                    vals['birth_date'] = patient.birth_date
                    vals['email'] = patient.email
                    vals['phone'] = patient.phone
                    vals['gender'] = patient.gender

            elif phone and patient_name:
                existing_patient = self.env['clinic.patient'].search([
                    ('phone', '=', phone),
                    ('name', '=', patient_name),
                ], limit=1)

                if existing_patient:
                    vals['patient_id'] = existing_patient.id
                    vals['patient_name'] = existing_patient.name
                    vals['birth_date'] = existing_patient.birth_date
                    vals['email'] = existing_patient.email
                    vals['gender'] = existing_patient.gender
                else:
                    patient = self.env['clinic.patient'].create({
                        'name': patient_name,
                        'birth_date': vals.get('birth_date'),
                        'email': vals.get('email'),
                        'phone': phone,
                        'gender': vals.get('gender'),
                    })
                    vals['patient_id'] = patient.id

            doctor_id = vals.get('doctor_id')
            appointment_date = vals.get('appointment_date')

            if doctor_id and appointment_date:
                last = self.search([
                    ('doctor_id', '=', doctor_id),
                    ('appointment_date', '=', appointment_date)
                ], order="token_number desc", limit=1)

                vals['token_number'] = (last.token_number or 0) + 1

        records = super().create(vals_list)

        for rec in records:
            if rec.slot_id:
                rec.slot_id.sudo().write({
                    'is_booked': True,
                    'appointment_id': rec.id
                })

        return records

    def write(self, vals):
        old_slots = {rec.id: rec.slot_id for rec in self}

        if 'patient_id' in vals and vals.get('patient_id'):
            patient = self.env['clinic.patient'].browse(vals['patient_id'])
            if patient.exists():
                vals['patient_name'] = patient.name
                vals['birth_date'] = patient.birth_date
                vals['email'] = patient.email
                vals['phone'] = patient.phone
                vals['gender'] = patient.gender

        elif ('phone' in vals or 'patient_name' in vals):
            for rec in self:
                phone = vals.get('phone', rec.phone)
                name = vals.get('patient_name', rec.patient_name)

                if phone and name:
                    patient = self.env['clinic.patient'].search([
                        ('phone', '=', phone),
                        ('name', '=', name),
                    ], limit=1)

                    if patient.exists():
                        vals.setdefault('patient_id', patient.id)
                        vals['patient_name'] = patient.name
                        vals['birth_date'] = patient.birth_date
                        vals['email'] = patient.email
                        vals['phone'] = patient.phone
                        vals['gender'] = patient.gender
                        break

        res = super().write(vals)

        for rec in self:
            old_slot = old_slots.get(rec.id)

            if old_slot and old_slot != rec.slot_id:
                old_slot.sudo().write({
                    'is_booked': False,
                    'appointment_id': False
                })

            if rec.slot_id:
                rec.slot_id.sudo().write({
                    'is_booked': True,
                    'appointment_id': rec.id
                })

        return res

    def unlink(self):
        for rec in self:
            if rec.slot_id:
                rec.slot_id.sudo().write({
                    'is_booked': False,
                    'appointment_id': False
                })
        return super().unlink()
    
    # ======================
    # ONCHANGE
    # ======================

    @api.onchange('phone', 'patient_name')
    def _onchange_phone(self):
        if self.phone and self.patient_name:
            patient = self.env['clinic.patient'].search([
                ('phone', '=', self.phone),
                ('name', '=', self.patient_name),
            ], limit=1)

            if patient:
                self.patient_id = patient.id
                self.patient_name = patient.name
                self.birth_date = patient.birth_date
                self.email = patient.email
                self.gender = patient.gender
            else:
                self.patient_id = False

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.patient_name = self.patient_id.name
            self.birth_date = self.patient_id.birth_date
            self.email = self.patient_id.email
            self.phone = self.patient_id.phone
            self.gender = self.patient_id.gender
    
    

    # ======================
    # LAB TEST ACTIONS
    # ======================

    def action_create_lab_test(self):
        self.ensure_one()

        if not self.lab_test_ids:
            raise UserError("Add lab tests first.")

        request = self.env['clinic.lab.request'].create({
            'appointment_id': self.id,
            'patient_name': self.patient_name,
            'doctor_id': self.doctor_id.id,
        })

        for test in self.lab_test_ids:
            self.env['clinic.lab.test.line'].create({
                'request_id': request.id,
                'test_id': test.test_id.id if test.test_id else False,
                'category': test.category,
                'name': test.name,
                'price': test.price,
                'code': test.code,
            })

        self.message_post(body=f"<b>Lab request {request.name} created.</b>")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Request',
            'res_model': 'clinic.lab.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }

   

    @api.onchange('lab_test_ids')
    def _onchange_lab_tests_update_notes(self):
        for rec in self:
            if rec.lab_test_ids:
                test_names = ", ".join([
                    name for name in rec.lab_test_ids.mapped('test_id.name') if name
                ])
                rec.doctor_notes = f"Lab tests requested: {test_names}."
            else:
                rec.doctor_notes = False

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    def action_print_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

        return self.env.ref('clinic_appointment.action_appointment_pdf_report').report_action(
            self.env['clinic.appointment'].search([]),
            data=data
        )

    # ======================
    # State
    # ======================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('in_consultation', 'In Consultation'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    # ======================
    # Consultation
    # ======================

    diagnosis_ids = fields.Many2many(
        'clinic.disease',
        string="Diagnoses",
        tracking=True
    )

    prescription = fields.Text(
        string="Prescription"
    )

    medicine_ids = fields.Many2many(
        'clinic.medicine',  # Links to medicine catalog
        string='Prescribed Medicines'
    )

    doctor_notes = fields.Text(
        string="Doctor Notes",
        tracking=True
    )

    # Link lab tests to appointment
    lab_test_ids = fields.One2many(
        'clinic.lab.test', 'appointment_id', string="Lab Tests",
    )

    
                
    next_action = fields.Selection([
        ('medicine', 'Medicine'),
        ('lab', 'Lab Test'),
        ('both', 'Medicine & Lab Test'),
        ('none', 'No Action')
    ],string="Next Action",tracking=True)

    followup_days = fields.Integer(
        string="Follow-up After (Days)",
        help="Doctor decides follow-up after consultation"
    )

    followup_date = fields.Date(
        string="Follow-up Date",
        compute="_compute_followup_date",
        store=True
    )

    followup_count = fields.Integer(compute="_compute_followups")
    overdue_count = fields.Integer(compute="_compute_followups")

    def _compute_followups(self):
        today = fields.Date.today()

        for rec in self:
            domain = [
                ('state', '=', 'done'),
                ('followup_date', '!=', False),
                ('patient_id', '=', rec.patient_id.id),  # ✅ important
            ]

            all_records = self.env['clinic.appointment'].search(domain)

            rec.followup_count = len(all_records)

            rec.overdue_count = len(all_records.filtered(
                lambda r: r.followup_date < today
            ))

    
    
    
    
    # ======================
    # Nurse Vitals
    # ======================

    bp = fields.Char(string="Blood Pressure")

    temperature = fields.Float(string="Temperature (°F)")

    pulse = fields.Integer(string="Pulse")

    weight = fields.Float(string="Weight (kg)")

    symptoms = fields.Text(string="Symptoms")

    

    
    # ======================
    # Receptionist Dashboard Stats
    # ======================

    today_appointments = fields.Integer(
        compute="_compute_reception_stats"
    )

    today_confirmed = fields.Integer(
        compute="_compute_reception_stats"
    )

    today_cancelled = fields.Integer(
        compute="_compute_reception_stats"
    )

    today_done_total = fields.Integer(
        compute="_compute_reception_stats"
    )

    @api.depends('state')
    def _compute_reception_stats(self):

        today = fields.Date.today()

        for rec in self:

            rec.today_appointments = self.search_count([
                ('appointment_date', '=', today)
            ])

            rec.today_confirmed = self.search_count([
                ('appointment_date', '=', today),
                ('state', '=', 'confirmed')
            ])

            rec.today_cancelled = self.search_count([
                ('appointment_date', '=', today),
                ('state', '=', 'cancelled')
            ])

            rec.today_done_total = self.search_count([
                ('appointment_date', '=', today),
                ('state', '=', 'done')
            ])
        
    
    # ======================
    # COMPUTE FOLLOW-UP DATE
    # ======================
    @api.depends('appointment_date', 'followup_days')
    def _compute_followup_date(self):
        for rec in self:
            if rec.appointment_date and rec.followup_days:
                appointment_date = fields.Date.from_string(rec.appointment_date)
                followup = appointment_date + timedelta(days=rec.followup_days)
                rec.followup_date = fields.Date.to_string(followup)
            else:
                rec.followup_date = False

    
    # ====================== 
    # Actions 
    # ====================== 
    def action_confirm(self): 
        for rec in self: 
            rec.state = 'confirmed' 
 
            rec.message_post(body="<b>Appointment Confirmed</b>") 
 
            template = self.env.ref( 
                'clinic_appointment.email_template_appointment_confirmed', 
                raise_if_not_found=False 
            ) 
            if template and rec.email: 
                template.send_mail(rec.id, force_send=True) 
 
    def action_done(self):
        for rec in self:

            rec.state = 'done'

            rec.message_post(
                body=f"<b>Consultation Completed</b><br/>Notes: {rec.doctor_notes or 'N/A'}"
            )

            # followup activity
            days = rec.followup_days or 14
            followup_date = fields.Date.today() + timedelta(days=days)

            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=rec.followup_date,
                summary="Follow-up with patient",
                user_id=self.env.user.id
            )

            # email
            template = self.env.ref(
                'clinic_appointment.email_template_consultation_done',
                raise_if_not_found=False
            )

            if template and rec.email:
                template.send_mail(rec.id, force_send=True)

    can_doctor_cancel = fields.Boolean(
        compute="_compute_can_doctor_cancel",
        store=False
    )

    @api.depends('create_date')
    def _compute_can_doctor_cancel(self):
        now = fields.Datetime.now()  # Odoo handles UTC internally

        for rec in self:
            if rec.create_date:
                limit_time = rec.create_date + timedelta(hours=24)
                rec.can_doctor_cancel = now <= limit_time
            else:
                rec.can_doctor_cancel = False

    def action_cancel(self):
        now = fields.Datetime.now()
        template = self.env.ref('clinic_appointment.email_template_appointment_cancelled')

        for rec in self:

            user = self.env.user

            # 🔴 Receptionist → MUST enter reason
            if user.has_group('clinic_appointment.group_clinic_receptionist') \
            and not user.has_group('clinic_appointment.group_clinic_doctor'):

                if not rec.cancel_reason:
                    raise UserError("Please enter a cancellation reason.")

                if rec.state != 'draft':
                    raise UserError("Receptionist can cancel only in draft state.")

                rec.state = 'cancelled'

                rec.message_post(
                    body=f"<b>Appointment Cancelled</b><br/>Reason: {rec.cancel_reason}"
                )

                template.send_mail(rec.id, force_send=True)
                continue

            # 👩‍⚕️ Doctor → reason optional (NO TIME LIMIT NOW)
            if user.has_group('clinic_appointment.group_clinic_doctor'):

                if not rec.cancel_reason:
                    doctor_name = user.name
                    cancel_time = format_datetime(self.env, now)

                    rec.cancel_reason = (
                        f"The appointment was cancelled by Dr. {doctor_name} on {cancel_time} "
                        "due to unforeseen circumstances."
                    )

            # 👤 Others (fallback)
            if not rec.cancel_reason:
                cancel_time = format_datetime(self.env, now)

                rec.cancel_reason = (
                    f"The appointment was cancelled on {cancel_time} "
                    "due to operational reasons."
                )

            # ✅ Final cancel
            rec.state = 'cancelled'

            rec.message_post(
                body=f"<b>Appointment Cancelled</b><br/>Reason: {rec.cancel_reason}"
            )

            template.send_mail(rec.id, force_send=True)

    
    show_cancel_field = fields.Boolean(
        compute="_compute_show_cancel_field"
    )

    @api.depends('create_date')
    def _compute_show_cancel_field(self):
        now = fields.Datetime.now()
        user = self.env.user

        for rec in self:
            rec.show_cancel_field = False

            # 👨‍⚕️ Doctor → only 24 hrs
            if user.has_group('clinic_appointment.group_clinic_doctor'):
                if rec.create_date:
                    if now <= rec.create_date + timedelta(hours=24):
                        rec.show_cancel_field = True

            # 👩‍💼 Receptionist/Admin → always visible
            elif user.has_group('clinic_appointment.group_clinic_receptionist') or \
                 user.has_group('base.group_system'):
                rec.show_cancel_field = True

    def action_check_in(self):

        for rec in self:

            if rec.state != 'confirmed':
                raise ValidationError("Patient must have confirmed appointment.")

            rec.state = 'checked_in'

            rec.message_post(
                body="<b>Patient Checked-in at Reception</b>"
            )
    
    def action_mark_waiting(self):

        for rec in self:

            if rec.state != 'checked_in':
                raise ValidationError("Patient must be checked-in first.")

            rec.state = 'waiting'

            rec.message_post(
                body="<b>Nurse completed vitals check</b>"
            )

    # ======================
    # CRON: SEND REMINDERS
    # ======================
    def cron_send_followup_reminders(self):
        today = fields.Date.today()

        records = self.search([
            ('state', '=', 'done'),
            ('followup_date', '!=', False),
            ('email', '!=', False),
        ])

        template = self.env.ref(
            'clinic_appointment.email_template_followup_reminder',
            raise_if_not_found=False
        )

        if not template:
            return

        for rec in records:
            days_left = (rec.followup_date - today).days

            # ✅ Only send before 1 or 2 days
            if days_left in (1, 2):
                template.send_mail(rec.id, force_send=True)


    # ======================
    # Onchange Specialization
    # ======================

    @api.onchange('specialization_id')
    def _onchange_specialization(self):
        self.doctor_id = False

        if not self.specialization_id:
            return

        name = self.specialization_id.name.lower()

        # -----------------------------
        # CATEGORY MAPPING
        # -----------------------------
        if any(x in name for x in ['cardio', 'heart']):
            self.followup_days = 14

        elif any(x in name for x in ['derma', 'cosmet', 'skin', 'hair', 'laser']):
            self.followup_days = 7

        elif any(x in name for x in ['ortho', 'bone', 'spine', 'joint']):
            self.followup_days = 21

        elif any(x in name for x in ['neuro', 'brain']):
            self.followup_days = 14

        elif any(x in name for x in ['gastro', 'liver', 'hepat']):
            self.followup_days = 10

        elif any(x in name for x in ['kidney', 'renal', 'nephro']):
            self.followup_days = 12

        elif any(x in name for x in ['lung', 'pulmo', 'respiratory']):
            self.followup_days = 10

        elif any(x in name for x in ['oncology', 'cancer']):
            self.followup_days = 7

        elif any(x in name for x in ['eye', 'ophthal', 'retina', 'glaucoma']):
            self.followup_days = 5

        elif any(x in name for x in ['ent', 'ear', 'nose', 'throat']):
            self.followup_days = 7

        elif any(x in name for x in ['dental', 'tooth', 'oral']):
            self.followup_days = 5

        elif any(x in name for x in ['physio', 'rehab']):
            self.followup_days = 3

        elif any(x in name for x in ['psycho', 'mental']):
            self.followup_days = 14

        elif any(x in name for x in ['diabet', 'endocrine', 'thyroid']):
            self.followup_days = 15

        elif any(x in name for x in ['preg', 'gyn', 'obstet']):
            self.followup_days = 10

        elif any(x in name for x in ['pediatric', 'child', 'neonat']):
            self.followup_days = 7

        elif any(x in name for x in ['emergency', 'trauma']):
            self.followup_days = 2

        else:
            self.followup_days = 10  # default


    # ======================
    # Age Calculation
    # ======================

    @api.depends('birth_date')
    def _compute_age(self):
        today = fields.Date.today()

        for rec in self:
            rec.age = ""

            if rec.birth_date:
                # Prevent future birth dates
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

    @api.constrains('birth_date')
    def _check_birth_date(self):

        today = fields.Date.today()

        for rec in self:
            if rec.birth_date:
                if rec.birth_date > today:
                    raise ValidationError(
                        "Birth date cannot be a future date."
                    )
    


    # ======================
    # Appointment Date Validation
    # ======================

    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        today = fields.Date.today()

        for rec in self:
            if rec.appointment_date and rec.appointment_date < today:
                raise ValidationError(
                    "Appointment date must be today or a future date."
                )

    


    # ======================
    # Specialization Match Validation
    # ======================

    @api.constrains('doctor_id', 'specialization_id')
    def _check_specialization_match(self):

        for rec in self:

            if rec.doctor_id.specialization_id != rec.specialization_id:

                raise ValidationError(
                    "Doctor does not match selected specialization."
                )
            
    
    @api.onchange('doctor_id', 'appointment_date')
    def _onchange_doctor_or_date(self):
        self.slot_id = False 
        if self.doctor_id and self.appointment_date:
            self.env['clinic.appointment.slot'].generate_slots(self.doctor_id, self.appointment_date)

    


    # ======================
    # Patient History
    # ======================

    def action_view_patient_history(self):
        self.ensure_one()

        domain = [('id', '!=', self.id)]
        if self.patient_id:
            domain.append(('patient_id', '=', self.patient_id.id))
        else:
            domain.extend([
                ('phone', '=', self.phone),
                ('patient_name', '=', self.patient_name)
            ])

        return {
            'name': 'Patient History',
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_patient_name': self.patient_name
            }
        }
    
    # ======================
    # Next Patient
    # ======================

    def action_next_patient(self):

        today = fields.Date.today()

        # 🔴 Step 1: complete current patient
        current = self.search([
            ('doctor_user_id', '=', self.env.user.id),
            ('appointment_date', '=', today),
            ('state', '=', 'in_consultation')
        ], limit=1)

        if current:
            current.state = 'done'

        # 🟢 Step 2: get next patient
        next_patient = self.search([
            ('doctor_user_id', '=', self.env.user.id),
            ('appointment_date', '=', today),
            ('state', '=', 'waiting')
        ], order="token_number asc", limit=1)

        if not next_patient:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Queue Finished',
                    'message': 'No more patients waiting',
                    'type': 'warning',
                }
            }

        # 🔵 Step 3: move to consultation
        next_patient.state = 'in_consultation'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.appointment',
            'res_id': next_patient.id,
            'view_mode': 'form',
            'target': 'current',
        }
    is_called = fields.Boolean(default=False)

    def action_call_token(self):
        for rec in self:
            rec.is_called = True
            rec.state = 'called'   # or keep 'waiting' based on your flow

            rec.message_post(
                body=f"<b>Token Called:</b> {rec.token_number}"
            )

    
        
    # ======================
    # Doctor Dashboard Stats
    # ======================

    today_total = fields.Integer(
        compute="_compute_today_stats"
    )

    today_done = fields.Integer(
        compute="_compute_today_stats"
    )

    today_pending = fields.Integer(
        compute="_compute_today_stats"
    )

    today_followups = fields.Integer(
        compute="_compute_today_stats"
    )

    @api.depends('doctor_user_id')
    def _compute_today_stats(self):

        today = fields.Date.today()

        for rec in self:

            domain = [
                ('doctor_user_id', '=', self.env.user.id),
                ('appointment_date', '=', today)
            ]

            rec.today_total = self.search_count(domain)

            rec.today_done = self.search_count(
                domain + [('state', '=', 'done')]
            )

            rec.today_pending = self.search_count(
                domain + [('state', '=', 'waiting')]
            )

            rec.today_followups = self.search_count([
                ('doctor_user_id', '=', self.env.user.id),
                ('followup_date', '=', today)
            ])

    _sql_constraints = [('unique_slot_booking', 'unique(slot_id)', 'This time slot is already booked.')]
    
    # ======================
    # Start Consultation
    # ======================

    def action_start_consultation(self):
        for rec in self:

            if rec.state != 'called':   # ✅ FIX HERE
                raise ValidationError("Consultation can start only after token is called")

            rec.state = 'in_consultation'

            rec.message_post(
                body="<b>Consultation Started</b>"
            )

    @api.constrains('doctor_id', 'appointment_date', 'appointment_time')
    def _check_double_booking(self):

        for rec in self:

            if not rec.doctor_id or not rec.appointment_date or not rec.appointment_time:
                continue
    
            
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



   
   # ====================== 
    # Start Consultation 
    # ====================== 
 
    def action_start_consultation(self): 
        for rec in self: 
 
            if rec.state != 'called':   # ✅ FIX HERE 
                raise ValidationError("Consultation can start only after token is called") 
 
            rec.state = 'in_consultation' 
 
            rec.message_post( 
                body="<b>Consultation Started</b>" 
            ) 
 
    @api.constrains('doctor_id', 'appointment_date', 'appointment_time') 
    def _check_double_booking(self): 
 
        for rec in self: 
 
            if not rec.doctor_id or not rec.appointment_date or not rec.appointment_time: 
                continue 
     
             
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
