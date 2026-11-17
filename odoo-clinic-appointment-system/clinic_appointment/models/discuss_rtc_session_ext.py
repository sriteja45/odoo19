from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

_logger.warning("RTC DEBUG: discuss_rtc_session_ext file imported")


class DiscussChannelRtcSessionExt(models.Model):
    _inherit = "discuss.channel.rtc.session"

    def unlink(self):
        _logger.warning("RTC DEBUG: unlink called for sessions: %s", self.ids)

        call_history_env = self.env["clinic.call.history"].sudo()

        for session in self:
            try:
                _logger.warning("RTC DEBUG: processing session id=%s", session.id)

                # Debug all available values
                _logger.warning("RTC DEBUG: session create_date=%s", session.create_date)

                channel_member = getattr(session, "channel_member_id", False)
                _logger.warning("RTC DEBUG: channel_member=%s", channel_member.id if channel_member else False)

                if not channel_member:
                    _logger.warning("RTC DEBUG: no channel_member_id on session %s", session.id)
                    continue

                channel = getattr(channel_member, "channel_id", False)
                _logger.warning("RTC DEBUG: channel=%s", channel.id if channel else False)

                if not channel:
                    _logger.warning("RTC DEBUG: no channel_id on channel_member %s", channel_member.id)
                    continue

                partner = getattr(channel_member, "partner_id", False)
                _logger.warning("RTC DEBUG: partner=%s", partner.id if partner else False)

                user = partner.user_ids[:1] if partner and partner.user_ids else self.env.user
                _logger.warning("RTC DEBUG: user=%s", user.id if user else False)

                start_dt = session.create_date or fields.Datetime.now()
                end_dt = fields.Datetime.now()

                duration_seconds = int((end_dt - start_dt).total_seconds())
                if duration_seconds < 0:
                    duration_seconds = 0

                if duration_seconds >= 60:
                    minutes = duration_seconds // 60
                    duration_text = f"{minutes} min"
                else:
                    duration_text = f"{duration_seconds} sec"

                note = f"RTC session ended. Duration: {duration_text}. Session ID: {session.id}"

                existing = call_history_env.search([
                    ("note", "ilike", f"Session ID: {session.id}")
                ], limit=1)
                if existing:
                    _logger.warning("RTC DEBUG: existing record found for session %s", session.id)
                    continue

                record = call_history_env.create({
                    "channel_id": channel.id,
                    "message_id": False,
                    "user_id": user.id if user else self.env.ref("base.user_admin").id,
                    "partner_id": partner.id if partner else False,
                    "call_datetime": end_dt,
                    "duration_seconds": duration_seconds,
                    "duration_text": duration_text,
                    "note": note,
                })

                _logger.warning(
                    "RTC DEBUG: call history created successfully. session=%s record=%s duration=%s",
                    session.id, record.id, duration_text
                )

            except Exception as e:
                _logger.exception("RTC DEBUG: failed for session %s: %s", session.id, e)

        return super().unlink()