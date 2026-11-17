from odoo import models, fields, api
import io
import base64
from openpyxl import Workbook

class ClinicAppointmentReport(models.TransientModel):
    _name = 'clinic.appointment.report'
    _description = 'Appointment Report'

    report_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half-Yearly'), 
        ('yearly', 'Yearly'),
    ], required=True)

    doctor_id = fields.Many2one(
        'clinic.employee',
        string="Doctor",
        domain=[('role', '=', 'doctor')]
    )

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    

    def action_generate_report(self):

        domain = [
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to)
        ]

        if self.doctor_id:
            domain.append(('doctor_id', '=', self.doctor_id.id))

        records = self.env['clinic.appointment'].search(domain)

        total = len(records)
        confirmed = len(records.filtered(lambda r: r.state == 'confirmed'))
        done = len(records.filtered(lambda r: r.state == 'done'))
        cancelled = len(records.filtered(lambda r: r.state == 'cancelled'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Report Generated',
                'message': f"Total: {total}, Done: {done}, Confirmed: {confirmed}, Cancelled: {cancelled}",
                'type': 'success',
            }
        }
    
   
    
    @api.onchange('report_type')
    def _onchange_report_type(self):
        today = fields.Date.today()

        if self.report_type == 'monthly':
            self.date_from = today.replace(day=1)
            self.date_to = today

        elif self.report_type == 'quarterly':
            month = ((today.month - 1) // 3) * 3 + 1
            self.date_from = today.replace(month=month, day=1)
            self.date_to = today

        elif self.report_type == 'half_yearly':  # ✅ NEW
            if today.month <= 6:
                self.date_from = today.replace(month=1, day=1)
            else:
                self.date_from = today.replace(month=7, day=1)
            self.date_to = today


        elif self.report_type == 'yearly':
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today

    def action_download_excel(self):
        domain = [
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to)
        ]

        if self.doctor_id:
            domain.append(('doctor_id', '=', self.doctor_id.id))

        records = self.env['clinic.appointment'].search(domain)

        wb = Workbook()
        ws = wb.active
        ws.title = "Appointments"

        # ✅ Report Title
        ws.append(['Clinic Appointment Report'])
        ws.append([])

        # ✅ Report Info
        ws.append(['Report Type', self.report_type])
        ws.append(['From Date', str(self.date_from)])
        ws.append(['To Date', str(self.date_to)])
        
        if self.doctor_id:
            ws.append(['Doctor', self.doctor_id.name])

        ws.append([])

        # ✅ Header
        ws.append([
            'Appointment ID', 'Patient', 'Doctor',
            'Date', 'State', 'Phone'
        ])

        # ✅ Data
        for rec in records:
            ws.append([
                rec.appointment_id,
                rec.patient_name,
                rec.doctor_id.name if rec.doctor_id else '',
                str(rec.appointment_date),
                rec.state,
                rec.phone
            ])

        # ✅ Summary Section (🔥 NEW)
        total = len(records)
        confirmed = len(records.filtered(lambda r: r.state == 'confirmed'))
        done = len(records.filtered(lambda r: r.state == 'done'))
        cancelled = len(records.filtered(lambda r: r.state == 'cancelled'))

        ws.append([])
        ws.append(['Summary'])
        ws.append(['Total', total])
        ws.append(['Confirmed', confirmed])
        ws.append(['Done', done])
        ws.append(['Cancelled', cancelled])

        # ✅ Half-Year Label (🔥 NEW)
        if self.report_type == 'half_yearly':
            ws.append([])
            if self.date_from.month == 1:
                ws.append(['Period', 'H1 (Jan - Jun)'])
            else:
                ws.append(['Period', 'H2 (Jul - Dec)'])

        # ✅ Save file
        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        file_data = base64.b64encode(file_stream.read())

        # ✅ Dynamic filename (🔥 NEW)
        file_name = f"Appointment_Report_{self.report_type}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def action_print_pdf(self):
        domain = [
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to)
        ]

        if self.doctor_id:
            domain.append(('doctor_id', '=', self.doctor_id.id))



        # ✅ FETCH REAL APPOINTMENTS

        appointments = self.env['clinic.appointment'].search(domain)



        # 🔥 IMPORTANT: pass appointments (NOT self)

        return self.env.ref(

        'clinic_appointment.report_appointment_pdf'

        ).with_context(
            date_from=self.date_from,
            date_to=self.date_to
        ).report_action(appointments)
    
    def action_view_analysis(self):
        domain = [
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to)
        ]

        if self.doctor_id:
            domain.append(('doctor_id', '=', self.doctor_id.id))

        if self.report_type == 'monthly':
            date_group = 'appointment_date:month'
        elif self.report_type == 'quarterly':
            date_group = 'appointment_date:quarter'
        elif self.report_type == 'half_yearly':
            date_group = 'appointment_date:month'
        else:
            date_group = 'appointment_date:year'

        # 🔥 FINAL FORCE LOGIC
        if self.doctor_id:
            group_by = ['state', date_group]
        else:
            group_by = ['doctor_id', date_group]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointment Analysis',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,graph,pivot',
            'domain': domain,

            'context': {
                # ✅ FORCE RESET EVERYTHING
                'group_by': group_by,
                'graph_measure': '__count__',
                'pivot_measures': ['__count__'],

                # 🔥 CRITICAL FIXES
                'search_default_group_by_state': 0,
                'search_default_group_by_doctor_id': 0,
                'search_default_group_by': 0,

                # 🔥 REMOVE ALL OLD GROUPS
                'group_by_no_leaf': 1,
                'group_by_context': [],
            },
        }