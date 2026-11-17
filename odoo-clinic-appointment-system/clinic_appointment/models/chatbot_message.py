from odoo import models, fields


class ClinicChatbotMessage(models.Model):
    _name = 'clinic.chatbot.message'
    _description = 'Clinic Chatbot Message'
    _order = 'create_date asc'

    session_id = fields.Many2one('clinic.chatbot.session', string='Session', required=True, ondelete='cascade')
    sender_type = fields.Selection([
        ('user', 'User'),
        ('bot', 'Bot'),
    ], required=True, string='Sender')
    user_id = fields.Many2one('res.users', string='User')
    content = fields.Text(string='Message', required=True)
    detected_module = fields.Selection([
        ('appointment', 'Appointments'),
        ('doctor', 'Doctors'),
        ('service', 'Services'),
        ('lab', 'Lab'),
        ('general', 'General'),
    ], string='Detected Module')
    detected_intent = fields.Char(string='Detected Intent')
    user_role_at_time = fields.Selection([
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('guest', 'Guest'),
    ], string='Role at Time')
