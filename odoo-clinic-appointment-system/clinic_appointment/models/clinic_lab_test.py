from odoo import models, fields, api
from odoo.exceptions import UserError

class ClinicLabTest(models.Model):
    _name = "clinic.lab.test"
    _description = "Lab Test Request"
    _order = "id desc"

    # Basic Info
    lab_id= fields.Char(string="Lab Test ID", default="New", readonly=True)
    appointment_id = fields.Many2one('clinic.appointment', string="Appointment")
    patient_name = fields.Char(string="Patient")
    description = fields.Text(string="Description")
    doctor_id = fields.Many2one('clinic.employee', string="Doctor", domain="[('role','=','doctor')]")
    technician_id = fields.Many2one('clinic.employee', string="Technician", domain="[('role','=','lab_technician')]")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    price = fields.Monetary(
        string="Price",
        currency_field='currency_id',
        required=True,
        help="Enter test cost"
    )
    # Lab Test details
    category = fields.Selection([
        ('hematology', 'Hematology'),
        ('biochemistry', 'Biochemistry'),
        ('liver', 'Liver Function'),
        ('cardiac', 'Cardiac'),
        ('thyroid', 'Thyroid & Hormones'),
        ('serology', 'Serology'),
        ('microbiology', 'Microbiology'),
        ('urine', 'Urine Tests'),
        ('stool', 'Stool Tests'),
        ('kidney', 'Kidney Function'),
        ('special', 'Special Tests'),
        ('coagulation', 'Coagulation'),
        ('women', 'Women Health'),
        ('pediatrics', 'Pediatrics'),
        ('orthopedic', 'Orthopedic'),
        ('autoimmune', 'Autoimmune'),
        ('respiratory', 'Respiratory'),
        ('oncology', 'Oncology'),
        ('imaging', 'Imaging'),
    ], string="Category", required=True)
    name = fields.Char(string="Test Name", required=True)

    code = fields.Char(string="Test Code")

    
    test_id = fields.Many2one('clinic.lab.test', string="Test Template", domain="[('is_template','=',True), ('category','=',category)]")
    priority = fields.Selection([('normal', 'Normal'), ('urgent', 'Urgent')], default='normal')

    # Process
    sample_collected = fields.Boolean(string="Sample Collected")
    status = fields.Selection([('requested','Requested'), ('processing','Processing'), ('completed','Completed')], default='requested')

    # Report
    report = fields.Binary(string="Lab Report")
    report_filename = fields.Char()
    report_date = fields.Date(readonly=True)
    remarks = fields.Text()
    
    is_template = fields.Boolean(default=False)

    @api.model
    def create(self, vals):

        # Handle multiple records
        if isinstance(vals, list):
            for v in vals:

                # ✅ Ensure name always exists
                if not v.get('name'):
                    if v.get('test_id'):
                        template = self.env['clinic.lab.test'].browse(v['test_id'])
                        v['name'] = template.name
                    else:
                        v['name'] = self.env['ir.sequence'].next_by_code('clinic.lab.test') or 'LAB0001'

                # ✅ Template logic
                if not v.get('appointment_id'):
                    v['is_template'] = True

                # ✅ Appointment autofill
                if v.get('appointment_id'):
                    appointment = self.env['clinic.appointment'].browse(v['appointment_id'])

                    if appointment.patient_name:
                        v['patient_name'] = appointment.patient_name

                    if appointment.doctor_id:
                        v['doctor_id'] = appointment.doctor_id.id

            return super().create(vals)

        # Handle single record
        else:

            # ✅ Ensure name always exists
            if not vals.get('name'):
                if vals.get('test_id'):
                    template = self.env['clinic.lab.test'].browse(vals['test_id'])
                    vals['name'] = template.name
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('clinic.lab.test') or 'LAB0001'

            # ✅ Template logic
            if not vals.get('appointment_id'):
                vals['is_template'] = True

            # ✅ Appointment autofill
            if vals.get('appointment_id'):
                appointment = self.env['clinic.appointment'].browse(vals['appointment_id'])

                if appointment.patient_name:
                    vals['patient_name'] = appointment.patient_name

                if appointment.doctor_id:
                    vals['doctor_id'] = appointment.doctor_id.id

            return super().create(vals)
            

        # Actions for lab technician
    def action_collect_sample(self):
        for rec in self:
            rec.write({'sample_collected': True, 'status': 'processing'})

    def action_complete_test(self):
        for rec in self:
            if not rec.sample_collected:
                raise UserError("⚠ Collect sample first.")
            if not rec.report:
                    raise UserError("⚠ Upload report first.")
            rec.write({'status': 'completed', 'report_date': fields.Date.today()})

    @api.onchange('report')
    def _onchange_report(self):
        if self.report:
            self.status = 'completed'
            self.report_date = fields.Date.today()

   

    # 👇 ADD THIS METHOD HERE
    @api.onchange('appointment_id')
    def _onchange_appointment_id(self):
        if self.appointment_id:
            
            self.doctor_id = self.appointment_id.doctor_id
            self.patient_name = self.appointment_id.patient_name

    @api.onchange('category')
    def _onchange_category(self):
        self.test_id = False

    
   