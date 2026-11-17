from odoo import models, fields, api
from odoo.exceptions import UserError


class ClinicLabRequest(models.Model):
    _name = 'clinic.lab.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lab Request'
    _order = 'id desc'

    name = fields.Char(default='New', readonly=True)
    appointment_id = fields.Many2one('clinic.appointment', string="Appointment")
    patient_name = fields.Char(string="Patient")
    doctor_id = fields.Many2one('clinic.employee', string="Doctor")
    category = fields.Many2one('clinic.lab.test', string='category')

    doctor_user_id = fields.Many2one(
        'res.users',
        string="Doctor User",
        related='doctor_id.user_id',
        store=True,
        readonly=True
    )

    request_date = fields.Date(default=fields.Date.today, string="Request Date")

    status = fields.Selection([
        ('requested', 'Requested'),
        ('processing', 'Processing'),
        ('completed', 'Completed')
    ], default='requested', tracking=True)

    line_ids = fields.One2many(
        'clinic.lab.test.line',
        'request_id',
        string="Tests"
    )

    total_amount = fields.Float(compute="_compute_total", string="Total Amount")

    @api.depends('line_ids.price')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('price'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('clinic.lab.request')
                vals['name'] = seq or 'REQ0001'

            if vals.get('appointment_id'):
                appointment = self.env['clinic.appointment'].browse(vals['appointment_id'])
                if appointment.exists():
                    vals.setdefault('patient_name', appointment.patient_name)
                    vals.setdefault('doctor_id', appointment.doctor_id.id)

        return super().create(vals_list)

    def action_mark_processing(self):
        for rec in self:
            rec.status = 'processing'
            rec.line_ids.write({'status': 'processing'})
            rec.message_post(body="<b>Lab request moved to Processing.</b>")

    def action_mark_completed(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Please add lab tests before completing the request.")

            missing_reports = rec.line_ids.filtered(lambda line: not line.report)
            if missing_reports:
                missing_names = ", ".join(missing_reports.mapped('name'))
                raise UserError(
                    f"Upload reports for all tests before completing.\nMissing: {missing_names}"
                )

            rec.status = 'completed'
            rec.line_ids.write({'status': 'done'})

            attachment_ids = []
            completed_tests = []

            for line in rec.line_ids:
                completed_tests.append(line.name or 'Test')

                if line.report:
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': line.report_filename or f"{line.name or 'lab_test'}_report.pdf",
                        'type': 'binary',
                        'datas': line.report,
                        'res_model': 'clinic.appointment',
                        'res_id': rec.appointment_id.id if rec.appointment_id else 0,
                        'mimetype': 'application/pdf',
                    })
                    attachment_ids.append(attachment.id)

            tests_html = "".join(f"<li>{test_name}</li>" for test_name in completed_tests)

            rec.message_post(body="<b>Lab request completed.</b>")

            if rec.appointment_id:
                rec.appointment_id.sudo().message_post(
                    body=f"""
                        <b>Lab Request Completed</b><br/>
                        Request: {rec.name}<br/>
                        Patient: {rec.patient_name}<br/>
                        Doctor: {rec.doctor_id.name if rec.doctor_id else ''}<br/>
                        <br/>
                        <b>Completed Tests:</b>
                        <ul>{tests_html}</ul>
                    """,
                    attachment_ids=attachment_ids
                )

                if rec.doctor_user_id:
                    rec.appointment_id.sudo().activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=rec.doctor_user_id.id,
                        summary="Lab reports ready",
                        note=f"Lab reports are ready for patient {rec.patient_name}. "
                             f"Request: {rec.name}. "
                             f"Tests: {', '.join(completed_tests)}"
                    )