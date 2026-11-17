from odoo import models, fields

class ClinicEnquiry(models.Model):
    _name = 'clinic.enquiry'
    _description = 'Patient Enquiry'
    _order = 'create_date desc'

    name = fields.Char(string="Patient Name", required=True)
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    department_id = fields.Many2one('clinic.department', string="Department")
    message = fields.Text(string="Message")
    reply = fields.Text(string="Reply")
    replied = fields.Boolean(string="Replied", default=False)

    def action_send_reply(self):
        for rec in self:
            rec.replied = True

            if rec.email:
                mail = self.env['mail.mail'].sudo().create({
                    'subject': 'Reply from ActiveLife Clinic',
                    'body_html': f"""
                        <p>Dear {rec.name},</p>
                        <p>{rec.reply}</p>
                        <br/>
                        <p>Thanks & Regards,<br/>ActiveLife Clinic</p>
                    """,
                    'email_to': rec.email,
                })
                mail.sudo().send()