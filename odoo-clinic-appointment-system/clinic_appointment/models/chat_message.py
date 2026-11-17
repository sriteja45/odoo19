from odoo import models, fields

class ClinicChatMessage(models.Model):
    _name = 'clinic.chat.message'
    _description = 'Chat Message'
    _order = 'create_date asc'
    
    session_id = fields.Many2one('clinic.chat.session', required=True, ondelete='cascade')
    sender_type = fields.Selection([
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('system', 'System')
    ], required=True)
    sender_name = fields.Char()
    message = fields.Text(required=True)
    is_read = fields.Boolean(default=False)
    read_timestamp = fields.Datetime()
    create_date = fields.Datetime(default=fields.Datetime.now)