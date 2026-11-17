from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class ClinicDashboard(models.Model):
    _name = 'clinic.dashboard'
    _description = 'Clinic Dashboard'

    name = fields.Char(default="Dashboard")

    # Counts
    monthly = fields.Integer(string="This Month")
    quarterly = fields.Integer(string="This Quarter")
    yearly = fields.Integer(string="This Year")

    # Averages
    monthly_avg = fields.Float(string="Monthly Avg")
    quarterly_avg = fields.Float(string="Quarterly Avg")
    yearly_avg = fields.Float(string="Yearly Avg")
    average = fields.Float(string="Overall Avg")

    # Growth
    monthly_growth = fields.Float(string="Monthly Growth %")
    quarterly_growth = fields.Float(string="Quarterly Growth %")
    yearly_growth = fields.Float(string="Yearly Growth %")
    half_yearly = fields.Integer(string="Half-Yearly")
    half_yearly_avg = fields.Float(string="Half-Yearly Avg")
    half_yearly_growth = fields.Float(string="Half-Yearly Growth %")

    today_appointments = fields.Integer(string="Today", compute="_compute_counts")
    weekly_appointments = fields.Integer(string="This Week", compute="_compute_counts")

    total_doctors = fields.Integer(string="Doctors", compute="_compute_extra_counts")
    total_patients = fields.Integer(string="Patients", compute="_compute_extra_counts")

    @api.depends()
    def _compute_extra_counts(self):
        for rec in self:
            rec.total_doctors = self.env['clinic.employee'].search_count([
                ('role', '=', 'doctor'),
                ('active', '=', True)
            ])

            rec.total_patients = self.env['clinic.patient'].search_count([])

    # 👨‍⚕️ OPEN DOCTORS
    def action_view_doctors(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Doctors',
            'res_model': 'clinic.employee',
            'view_mode': 'kanban,list,form',
            'domain': [('role', '=', 'doctor')],
        }


    # 🧑‍🤝‍🧑 OPEN PATIENTS
    def action_view_patients(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Patients',
            'res_model': 'clinic.patient',
            'view_mode': 'list,form',
        }


    # 📅 TODAY APPOINTMENTS
    def action_view_today_appointments(self):
        today = fields.Date.today()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Today Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [('appointment_date', '=', today)],
        }


    # 📊 WEEKLY APPOINTMENTS
    def action_view_weekly_appointments(self):
        today = fields.Date.today()
        last_7_days = today - timedelta(days=7)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Weekly Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [
                ('appointment_date', '>=', last_7_days),
                ('appointment_date', '<=', today)
            ],
        }

    # ---------------- DASHBOARD LOAD ----------------
    def load_dashboard(self):
        today = fields.Date.today()
        Appointment = self.env['clinic.appointment']

        # ================= MONTH =================
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)

        prev_month_start = month_start - relativedelta(months=1)
        prev_month_end = month_start - relativedelta(days=1)

        current_month = Appointment.search_count([
            ('appointment_date', '>=', month_start),
            ('appointment_date', '<=', month_end)
        ])

        prev_month = Appointment.search_count([
            ('appointment_date', '>=', prev_month_start),
            ('appointment_date', '<=', prev_month_end)
        ])

        self.monthly = current_month

        # Avg per day (correct)
        days_in_month = (month_end - month_start).days + 1
        self.monthly_avg = round(current_month / days_in_month, 2) if days_in_month else 0

        self.monthly_growth = ((current_month - prev_month) / prev_month * 100) if prev_month else 0

        # ================= QUARTER =================
        quarter = (today.month - 1) // 3
        start_month = quarter * 3 + 1

        quarter_start = today.replace(month=start_month, day=1)
        quarter_end = quarter_start + relativedelta(months=3, days=-1)

        prev_q_start = quarter_start - relativedelta(months=3)
        prev_q_end = quarter_start - relativedelta(days=1)

        current_q = Appointment.search_count([
            ('appointment_date', '>=', quarter_start),
            ('appointment_date', '<=', quarter_end)
        ])

        prev_q = Appointment.search_count([
            ('appointment_date', '>=', prev_q_start),
            ('appointment_date', '<=', prev_q_end)
        ])

        self.quarterly = current_q

        # Avg per month in quarter
        self.quarterly_avg = round(current_q / 3, 2)

        self.quarterly_growth = ((current_q - prev_q) / prev_q * 100) if prev_q else 0

        # ================= HALF YEAR =================
        if today.month <= 6:
            # H1 → Jan to Jun
            half_start = today.replace(month=1, day=1)
            half_end = today.replace(month=6, day=30)
        else:
            # H2 → Jul to Dec
            half_start = today.replace(month=7, day=1)
            half_end = today.replace(month=12, day=31)

        prev_half_start = half_start - relativedelta(months=6)
        prev_half_end = half_start - relativedelta(days=1)

        current_half = Appointment.search_count([
            ('appointment_date', '>=', half_start),
            ('appointment_date', '<=', half_end)
        ])

        prev_half = Appointment.search_count([
            ('appointment_date', '>=', prev_half_start),
            ('appointment_date', '<=', prev_half_end)
        ])

        self.half_yearly = current_half

        # ✅ Avg per month (6 months)
        self.half_yearly_avg = round(current_half / 6, 2)

        # ✅ Growth %
        self.half_yearly_growth = ((current_half - prev_half) / prev_half * 100) if prev_half else 0

        # ================= YEAR =================
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)

        prev_year_start = year_start - relativedelta(years=1)
        prev_year_end = year_start - relativedelta(days=1)

        current_year = Appointment.search_count([
            ('appointment_date', '>=', year_start),
            ('appointment_date', '<=', year_end)
        ])

        prev_year = Appointment.search_count([
            ('appointment_date', '>=', prev_year_start),
            ('appointment_date', '<=', prev_year_end)
        ])

        self.yearly = current_year

        # Avg per month
        self.yearly_avg = round(current_year / 12, 2)

        self.yearly_growth = ((current_year - prev_year) / prev_year * 100) if prev_year else 0

        # ================= OVERALL =================
        months_passed = today.month or 1
        self.average = round(current_year / months_passed, 2)

    # ---------------- REPORT ACTIONS ----------------

    # 📅 Monthly
    def action_view_monthly_appointments(self):
        today = fields.Date.today()
        start = today.replace(day=1)
        end = start + relativedelta(months=1, days=-1)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Monthly Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [('appointment_date', '>=', start), ('appointment_date', '<=', end)],
        }

    # 📊 Quarterly (CORRECT ✅)
    def action_view_quarterly_appointments(self):
        today = fields.Date.today()

        # Get quarter start
        quarter = (today.month - 1) // 3
        start_month = quarter * 3 + 1

        start = today.replace(month=start_month, day=1)

        # ✅ IMPORTANT: FULL 3 MONTHS
        end = start + relativedelta(months=3, days=-1)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Quarterly Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [
                ('appointment_date', '>=', start),
                ('appointment_date', '<=', end)
            ],
        }
    
    def action_view_half_yearly_appointments(self):
        today = fields.Date.today()

        if today.month <= 6:
            start = today.replace(month=1, day=1)
            end = today.replace(month=6, day=30)
        else:
            start = today.replace(month=7, day=1)
            end = today.replace(month=12, day=31)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Half-Yearly Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [
                ('appointment_date', '>=', start),
                ('appointment_date', '<=', end)
            ],
        }

    # 📆 Yearly
    def action_view_yearly_appointments(self):
        today = fields.Date.today()
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Yearly Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [('appointment_date', '>=', start), ('appointment_date', '<=', end)],
        }
    
    appointment_ids = fields.One2many(
        'clinic.appointment',
        compute='_compute_appointments'
    )

    def _compute_appointments(self):
        for rec in self:
            rec.appointment_ids = self.env['clinic.appointment'].search([])

    # 📊 Monthly Average Report
    def action_view_monthly_avg(self):
        return self.action_view_monthly_appointments()

    # 📊 Quarterly Average
    def action_view_quarterly_avg(self):
        today = fields.Date.today()
        quarter = (today.month - 1) // 3
        start_month = quarter * 3 + 1
        start = today.replace(month=start_month, day=1)
        end = today  # only up to today
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quarterly Appointments (Avg)',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [('appointment_date', '>=', start), ('appointment_date', '<=', end)],
        }
    
    # 📆 Half-Yearly Average
    def action_view_half_yearly_avg(self):
        today = fields.Date.today()
        if today.month <= 6:
            start = today.replace(month=1, day=1)
        else:
            start = today.replace(month=7, day=1)
        
        end = today  # only up to today

        return {
            'type': 'ir.actions.act_window',
            'name': 'Half-Yearly Appointments (Avg)',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [
                ('appointment_date', '>=', start),
                ('appointment_date', '<=', end)
            ],
        }

    # 📊 Yearly Average Report
    def action_view_yearly_avg(self):
        return self.action_view_yearly_appointments()

    # ---------------- INIT ----------------
    @api.model
    def create_dashboard_record(self):
        if not self.search([], limit=1):
            self.create({'name': 'Dashboard'})

    def init(self):
        self.create_dashboard_record()

    

    

    user_id = fields.Many2one('res.users', string="Current User", default=lambda self: self.env.user)
    user_initial = fields.Char(string="User Initial", compute="_compute_user_initial")
    company_id = fields.Many2one('res.company', string='Company', related='user_id.company_id', readonly=True)

    @api.depends('user_id')
    def _compute_user_initial(self):
        for rec in self:
            rec.user_initial = rec.user_id.name[:1] if rec.user_id else ''

    @api.depends()
    def _compute_counts(self):
        for rec in self:
            today = fields.Date.today()

            # ✅ Today count
            rec.today_appointments = self.env['clinic.appointment'].search_count([
                ('appointment_date', '=', today)
            ])

            # ✅ Last 7 days
            last_7_days = today - timedelta(days=7)

            rec.weekly_appointments = self.env['clinic.appointment'].search_count([
                ('appointment_date', '>=', last_7_days),
                ('appointment_date', '<=', today)
            ])
    followup_count = fields.Integer(compute="_compute_followup_dashboard")
    overdue_count = fields.Integer(compute="_compute_followup_dashboard")

    def _compute_followup_dashboard(self):
        today = fields.Date.today()

        domain = [
            ('state', '=', 'done'),
            ('followup_date', '!=', False),
        ]

        for rec in self:
            # ✅ Total (Upcoming + Overdue)
            rec.followup_count = self.env['clinic.appointment'].search_count(domain)

            # 🔴 Overdue only
            rec.overdue_count = self.env['clinic.appointment'].search_count(
                domain + [('followup_date', '<', today)]
            )

    is_overdue_high = fields.Boolean(compute="_compute_is_overdue_high")

    def _compute_is_overdue_high(self):
        for rec in self:
            rec.is_overdue_high = rec.overdue_count > 5

    def action_view_followups(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Follow-ups',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'done'), ('followup_date', '!=', False)],
        }