from odoo import models, fields, api


class ClinicChatbotSession(models.Model):
    _name = 'clinic.chatbot.session'
    _description = 'Clinic Chatbot Session'
    _order = 'create_date desc'

    name = fields.Char(string='Session', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User')
    visitor_name = fields.Char(string='Visitor')
    user_role = fields.Selection([
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('guest', 'Guest'),
    ], string='Role', compute='_compute_user_role', store=True)
    message_ids = fields.One2many('clinic.chatbot.message', 'session_id', string='Messages')
    message_count = fields.Integer(compute='_compute_message_count')
    active_module = fields.Selection([
        ('appointment', 'Appointments'),
        ('doctor', 'Doctors'),
        ('service', 'Services'),
        ('lab', 'Lab'),
        ('general', 'General'),
    ], string='Active Module')
    state = fields.Selection([
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], default='active', string='State')
    agno_thread_id = fields.Char(string='Agno Thread ID')

    @api.depends('user_id', 'visitor_name', 'create_date')
    def _compute_name(self):
        for rec in self:
            who = rec.user_id.name or rec.visitor_name or 'Visitor'
            rec.name = f"Session - {who} - {rec.create_date}"

    @api.depends('user_id')
    def _compute_user_role(self):
        for rec in self:
            if not rec.user_id or rec.user_id._is_public():
                rec.user_role = 'guest'
            elif rec.user_id.has_group('base.group_system') or rec.user_id.has_group('clinic_appointment.group_clinic_receptionist'):
                rec.user_role = 'admin'
            else:
                rec.user_role = 'staff'

    @api.depends('message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    def action_close_session(self):
        self.write({'state': 'closed'})
