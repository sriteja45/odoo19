from odoo import models, fields, api
from odoo.exceptions import UserError


class ClinicLabTestLine(models.Model):
    _name = 'clinic.lab.test.line'
    _description = 'Lab Test Line'

    request_id = fields.Many2one(
        'clinic.lab.request',
        string="Lab Request",
        ondelete='cascade'
    )

    test_id = fields.Many2one(
        'clinic.lab.test',
        string="Test Template",
        domain="[('is_template','=',True)]"
    )

    name = fields.Char(string="Test Name")
    category = fields.Selection(
        
        related="test_id.category",
        string="Category",
        store=True,
        readonly=True
    )
    code = fields.Char(string="Code")
    price = fields.Float(string="Price")

    status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done')
    ], default='pending', string="Status")

    report = fields.Binary(string="Report", attachment=True)
    report_filename = fields.Char(string="Report Filename")


    @api.onchange('test_id')
    def _onchange_test(self):
        if self.test_id:
            self.name = self.test_id.name
            self.price = self.test_id.price
            self.code = self.test_id.code
            self.category = self.test_id.category

    def action_view_report(self):
        self.ensure_one()

        if not self.report:
            raise UserError("No report uploaded for this test.")

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=clinic.lab.test.line&id=%s&field=report&filename_field=report_filename&download=false' % self.id,
            'target': 'new',
        }
