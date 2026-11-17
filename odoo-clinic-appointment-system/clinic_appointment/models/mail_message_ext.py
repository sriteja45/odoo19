from odoo import models, api, fields
import re
import logging

_logger = logging.getLogger(__name__)


class MailMessageExt(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            body = record.body or ""
            clean_body = re.sub(r"<[^>]+>", "", body or "")
            clean_body = clean_body.replace("&nbsp;", " ").strip().lower()

            _logger.warning("CALL DEBUG BODY: %s", clean_body)
            _logger.warning("CALL DEBUG MODEL: %s", record.model)
            _logger.warning("CALL DEBUG RES_ID: %s", record.res_id)

            if "call lasted" not in clean_body:
                continue

            match = re.search(r"(\d+)\s*(sec|seconds|min|minute|minutes)", clean_body)
            duration_seconds = 0
            duration_text = ""

            if match:
                value = int(match.group(1))
                unit = match.group(2)

                if "min" in unit:
                    duration_seconds = value * 60
                    duration_text = f"{value} min"
                else:
                    duration_seconds = value
                    duration_text = f"{value} sec"

            channel = False

            # Main case
            if record.model == "discuss.channel" and record.res_id:
                channel = self.env["discuss.channel"].sudo().browse(record.res_id)

            # Fallback
            if (not channel or not channel.exists()) and record.res_id:
                possible_channel = self.env["discuss.channel"].sudo().browse(record.res_id)
                if possible_channel.exists():
                    channel = possible_channel

            if not channel or not channel.exists():
                _logger.warning("CALL DEBUG: channel not found for message %s", record.id)
                continue

            existing = self.env["clinic.call.history"].sudo().search([
                ("message_id", "=", record.id)
            ], limit=1)
            if existing:
                _logger.warning("CALL DEBUG: already saved message %s", record.id)
                continue

            user = self.env.user if self.env.user and self.env.user.exists() else self.env.ref("base.user_admin")
            partner = user.partner_id if user and user.partner_id else False

            self.env["clinic.call.history"].sudo().create({
                "channel_id": channel.id,
                "message_id": record.id,
                "user_id": user.id,
                "partner_id": partner.id if partner else False,
                "call_datetime": fields.Datetime.now(),
                "duration_seconds": duration_seconds,
                "duration_text": duration_text,
                "note": clean_body,
            })

            _logger.warning("CALL DEBUG: clinic.call.history created for message %s", record.id)

        return records