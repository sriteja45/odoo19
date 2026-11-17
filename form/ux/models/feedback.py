from odoo import fields, models


class UxFormFeedback(models.Model):
    _name = 'ux_form.feedback'
    _description = 'Website Customer Feedback'
    _order = 'create_date desc'

    name = fields.Char(string='Full Name', required=True)
    email = fields.Char(string='Email Address', required=True)
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Rating', required=True)
    headline = fields.Char(string='Summary / Description')
    feedback = fields.Text(string='Detailed Feedback', required=True)
