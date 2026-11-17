from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError

class ClinicEmployee(models.Model):
    _name = 'clinic.employee'
    _description = 'Clinic Employee'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ----------------------
    # Basic Information
    # ----------------------
    name = fields.Char(string="Employee Name", required=True)
    employee_code = fields.Char(string="Employee ID")
    role = fields.Selection([
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
        ('nurse', 'Nurse'),
        ('lab', 'Lab Technician'),
        ('pharmacist', 'Pharmacist'),
        ('housekeeping', 'Housekeeping'),
        ('other staff', 'Other Staff')
    ], string="Role", required=True)
    receptionist_specialization = fields.Selection([
        ('front_desk', 'Front Desk Executive'),
        ('billing', 'Billing Executive'),
        ('insurance', 'Insurance Coordinator'),
        ('appointment', 'Appointment Coordinator'),
        ('admission', 'Patient Admission Coordinator'),
        ('records', 'Medical Records Handler'),
    ], string="Receptionist Specialization")
    nurse_specialization = fields.Selection([
        ('general', 'General Nurse'),
        ('icu', 'ICU Nurse'),
        ('ot', 'Operation Theatre Nurse'),
        ('emergency', 'Emergency Nurse'),
        ('pediatric', 'Pediatric Nurse'),
        ('maternity', 'Maternity Nurse'),
        ('ward', 'Ward Nurse'),
        ('dialysis', 'Dialysis Nurse'),
        ('oncology', 'Oncology Nurse'),
    ], string="Nurse Specialization")
    lab_specialization = fields.Selection([
        ('pathology', 'Pathology Technician'),
        ('radiology', 'Radiology Technician'),
        ('xray', 'X-Ray Technician'),
        ('mri', 'MRI Technician'),
        ('ct_scan', 'CT Scan Technician'),
        ('ecg', 'ECG Technician'),
        ('blood_bank', 'Blood Bank Technician'),
        ('microbiology', 'Microbiology Technician'),
        ('biochemistry', 'Biochemistry Technician'),
        ('sample_collection', 'Sample Collection Technician'),
    ], string="Lab Specialization")
    # ----------------------
    # Contact Information
    # ----------------------
    mobile = fields.Char(string="Mobile")
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')], string="Gender")

    # ----------------------
    # Professional Information
    # ----------------------
    specialization_id = fields.Many2one(
        'clinic.specialization',
        string="Specialization"
    )
    qualification = fields.Char(string="Qualification")
    experience_years = fields.Integer(string="Experience (Years)")
    license_number = fields.Char(string="Medical License Number")

    # ----------------------
    # Work Information
    # ----------------------
    joining_date = fields.Date(string="Joining Date")
    department_id = fields.Many2one(
        'clinic.department',
        string="Department",
        ondelete='set null',
        help="Select the department or create a new one."
    )
    display_specialization = fields.Char(
    string="Specialization",
    compute="_compute_display_specialization",
    store=True
    )

    # Doctor Specific
    consultation_fee = fields.Float(string="Consultation Fee")
    max_patients_per_day = fields.Integer(string="Max Patients Per Day")

    # Availability
    available_from = fields.Float(string="Available From (24h)")
    available_to = fields.Float(string="Available To (24h)")

    # Profile
    image = fields.Binary(string="Profile Image")

    # Status
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Notes")

    image_url = fields.Char("Image URL", compute="_compute_image_url")

    @api.depends('role', 'gender')
    def _compute_image_url(self):
        for rec in self:
            role = rec.role or ''
            gender = rec.gender or ''

            # DEFAULT
            img = '/clinic_appointment/static/description/male_doctor.png'

            if role == 'doctor':
                img = '/clinic_appointment/static/description/female_doctor.png' if gender == 'female' else '/clinic_appointment/static/description/male_doctor.png'

            elif role == 'nurse':
                img = '/clinic_appointment/static/description/female_nurse.png' if gender == 'female' else '/clinic_appointment/static/description/male_nurse.png'

            elif role == 'lab':
                img = '/clinic_appointment/static/description/female_lab_technician.png' if gender == 'female' else '/clinic_appointment/static/description/male_lab_technician.png'

            elif role == 'receptionist':
                img = '/clinic_appointment/static/description/female_receptionist.png' if gender == 'female' else '/clinic_appointment/static/description/male_receptionist.png'

            rec.image_url = img

    @api.depends('role', 'specialization_id', 'receptionist_specialization', 'nurse_specialization', 'lab_specialization')
    def _compute_display_specialization(self):
        receptionist_map = {
            'front_desk': 'Front Desk Executive',
            'billing': 'Billing Executive',
            'insurance': 'Insurance Coordinator',
            'appointment': 'Appointment Coordinator',
            'admission': 'Patient Admission Coordinator',
            'records': 'Medical Records Handler',
        }

        nurse_map = {
            'general': 'General Nurse',
            'icu': 'ICU Nurse',
            'ot': 'Operation Theatre Nurse',
            'emergency': 'Emergency Nurse',
            'pediatric': 'Pediatric Nurse',
            'maternity': 'Maternity Nurse',
            'ward': 'Ward Nurse',
            'dialysis': 'Dialysis Nurse',
            'oncology': 'Oncology Nurse',
        }

        lab_map = {
            'pathology': 'Pathology Technician',
            'radiology': 'Radiology Technician',
            'xray': 'X-Ray Technician',
            'mri': 'MRI Technician',
            'ct_scan': 'CT Scan Technician',
            'ecg': 'ECG Technician',
            'blood_bank': 'Blood Bank Technician',
            'microbiology': 'Microbiology Technician',
            'biochemistry': 'Biochemistry Technician',
            'sample_collection': 'Sample Collection Technician',
        }

        for rec in self:
            if rec.role == 'doctor' and rec.specialization_id:
                rec.display_specialization = rec.specialization_id.name
            elif rec.role == 'receptionist' and rec.receptionist_specialization:
                rec.display_specialization = receptionist_map.get(rec.receptionist_specialization, '')
            elif rec.role == 'nurse' and rec.nurse_specialization:
                rec.display_specialization = nurse_map.get(rec.nurse_specialization, '')
            elif rec.role == 'lab' and rec.lab_specialization:
                rec.display_specialization = lab_map.get(rec.lab_specialization, '')
            else:
                rec.display_specialization = ''

    # ----------------------
    # Internal User Link
    # ----------------------
    user_id = fields.Many2one('res.users', string="Odoo User", readonly=True)
    send_invitation = fields.Boolean(string="Send Invitation Email", default=False)

    # ---------------------------------------------------------
    # GROUPS (ROLE BASED + MANUAL)
    # ---------------------------------------------------------
    group_id = fields.Many2many(
        'res.groups',
        string="Groups"
    )

    # ---------------------------------------------------------
    # ROLE → GROUP MAPPING
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # MAP ROLE TO GROUPS
    # ---------------------------------------------------------
    def _get_role_groups(self, role):
        role_group_map = {
            'doctor': [
                'clinic_appointment.group_clinic_doctor',
                'clinic_appointment.group_doctor_extra_access',
            ],
            'receptionist': [
                'clinic_appointment.group_clinic_receptionist',
                'clinic_appointment.group_receptionist_extra_access',
            ],
            'nurse': [
                'clinic_appointment.group_clinic_nurse',
                'clinic_appointment.group_nurse_extra_access',
            ],
            'lab': [
                'clinic_appointment.group_clinic_lab',
                'clinic_appointment.group_lab_extra_access',
            ],
            'pharmacist': [
                'clinic_appointment.group_clinic_pharmacist',
                'clinic_appointment.group_pharmacist_extra_access',
            ],
        }
        groups = []
        xml_ids = role_group_map.get(role, [])
        for xml in xml_ids:
            group = self.env.ref(xml, raise_if_not_found=False)
            if group:
                groups.append(group.id)
        return groups

    # ---------------------------------------------------------
    # AUTO ASSIGN GROUP WHEN ROLE CHANGES
    # ---------------------------------------------------------
    @api.onchange('role')
    def _onchange_role(self):
        for emp in self:
            groups = []
            internal_user = self.env.ref('base.group_user', raise_if_not_found=False)
            if internal_user:
                groups.append(internal_user.id)
            role_groups = emp._get_role_groups(emp.role)
            groups += role_groups
            emp.group_id = [(6, 0, groups)]

    # ---------------------------------------------------------
    # CREATE OR UPDATE INTERNAL USER
    # ---------------------------------------------------------
    def _create_or_update_user(self):
        for emp in self:
            login_email = emp.email or f"{emp.name.lower().replace(' ', '_')}@clinic.com"
            groups = emp.group_id.ids

            if not emp.user_id:
                # CREATE NEW USER
                user_vals = {
                    'name': emp.name,
                    'login': login_email,
                    'email': login_email,
                    'group_ids': [(6, 0, groups)],  # ✅ Odoo 19 correct
                }
                user = self.env['res.users'].sudo().create(user_vals)
                emp.user_id = user
            else:
                # UPDATE EXISTING USER
                emp.user_id.sudo().write({
                    'name': emp.name,
                    'email': emp.email,
                    'group_ids': [(6, 0, groups)]
                })

            # SEND PASSWORD RESET / INVITATION
            if emp.send_invitation and emp.user_id:
                emp.user_id.with_context(mail_create_nosubscribe=True).action_reset_password()

    # ---------------------------------------------------------
    # CREATE RECORD
    # ---------------------------------------------------------
    @api.model
    def create(self, vals):
        record = super().create(vals)
        groups = []

        internal_user = record.env.ref('base.group_user', raise_if_not_found=False)
        if internal_user:
            groups.append(internal_user.id)

        role_groups = record._get_role_groups(record.role)
        groups += role_groups

        record.group_id = [(6, 0, groups)]
        record._create_or_update_user()
        return record

    # ---------------------------------------------------------
    # UPDATE RECORD
    # ---------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            if 'role' in vals:
                groups = []
                internal_user = rec.env.ref('base.group_user', raise_if_not_found=False)
                if internal_user:
                    groups.append(internal_user.id)
                role_groups = rec._get_role_groups(rec.role)
                groups += role_groups
                rec.group_id = [(6, 0, groups)]

        if any(field in vals for field in ['role', 'group_id', 'email', 'name']):
            self._create_or_update_user()
        return res

    # ---------------------------------------------------------
    # BUTTON: CREATE INTERNAL USER
    # ---------------------------------------------------------
    def action_create_user(self):
        for emp in self:
            if emp.user_id:
                emp.message_post(body=_("Internal user already exists."))
                continue
            emp._create_or_update_user()
            emp.message_post(body=_("Internal user created successfully."))

    # ---------------------------------------------------------
    # BUTTON: SEND INVITATION EMAIL
    # ---------------------------------------------------------
    def action_send_invitation(self):
        for emp in self:
            if not emp.user_id:
                raise UserError(_("Please create the internal user first."))
            emp.user_id.with_context(mail_create_nosubscribe=True).action_reset_password()
        return True
     # ======================
    # Live Chat Status
    # ======================
    online_status = fields.Selection([
        ('offline', 'Offline'),
        ('online', 'Online'),
        ('busy', 'Busy')
    ], string="Online Status", default='offline')

    def action_go_online(self):
        for doctor in self:
            if doctor.role == 'doctor':
                doctor.online_status = 'online'
                doctor.message_post(body="✅ Doctor went online for live chat")
        return True

    def action_go_offline(self):
        for doctor in self:
            if doctor.role == 'doctor':
                doctor.online_status = 'offline'
                doctor.message_post(body="🔴 Doctor went offline")
        return True