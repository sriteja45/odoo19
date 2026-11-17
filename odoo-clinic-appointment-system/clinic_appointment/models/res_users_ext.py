from odoo import models, fields


class ResUsersExt(models.Model):
    _inherit = 'res.users'

    clinic_chatbot_role = fields.Selection([
        ('admin', 'Clinic Admin'),
        ('staff', 'Clinic Staff'),
        ('guest', 'Guest'),
    ], default='staff', string='Clinic Chatbot Role')

    clinic_chatbot_session_ids = fields.One2many(
        'clinic.chatbot.session', 'user_id', string='Clinic Chat Sessions'
    )
    clinic_chatbot_session_count = fields.Integer(compute='_compute_session_count')

    def _compute_session_count(self):
        for rec in self:
            rec.clinic_chatbot_session_count = len(rec.clinic_chatbot_session_ids)
