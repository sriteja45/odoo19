from odoo import api, fields, models


class ClinicCallHistory(models.Model):
    _name = "clinic.call.history"
    _description = "Clinic Discuss Call History"
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )

    channel_id = fields.Many2one(
        "discuss.channel",
        string="Discuss Channel",
        required=True,
        ondelete="cascade",
    )

    message_id = fields.Many2one(
        "mail.message",
        string="Message",
        ondelete="set null",
    )

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        default=lambda self: self.env.user,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        default=lambda self: self.env.user.partner_id,
    )

    call_datetime = fields.Datetime(
        string="Call Date & Time",
        default=fields.Datetime.now,
        required=True,
    )

    duration_seconds = fields.Integer(string="Duration (Seconds)", default=0)
    duration_text = fields.Char(string="Duration Text")
    note = fields.Text(string="Note")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("clinic.call.history") or "New"
        return super().create(vals_list)