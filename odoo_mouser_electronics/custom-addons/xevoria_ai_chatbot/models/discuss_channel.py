import logging
import re
import markdown
from odoo import api, models
from markupsafe import Markup
from ..services.ai_service import AIService

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    # ==========================================================
    # Automatic AI Trigger
    # ==========================================================

    def _notify_thread(self, message, msg_vals=False, **kwargs):

        result = super()._notify_thread(
            message,
            msg_vals=msg_vals,
            **kwargs,
        )

        # -----------------------------------------
        # Prevent recursion
        # -----------------------------------------

        if self.env.context.get("ai_reply"):
            return result

        # -----------------------------------------
        # LiveChat only
        # -----------------------------------------

        if self.channel_type != "livechat":
            return result

        # -----------------------------------------
        # Ignore OdooBot
        # -----------------------------------------

        odoobot = self.env.ref(
            "base.partner_root",
            raise_if_not_found=False,
        )

        if odoobot and message.author_id == odoobot:
            return result

        # -----------------------------------------
        # Clean HTML
        # -----------------------------------------

        prompt = message.body or ""

        prompt = re.sub(
            "<[^<]+?>",
            "",
            prompt,
        ).strip()

        if not prompt:
            return result

        # -----------------------------------------
        # Trigger AI
        # -----------------------------------------

        self._ask_ai(prompt)

        return result

    # ==========================================================
    # Shared AI Method
    # ==========================================================

    def _ask_ai(self, prompt):
        """
        Calls AI backend and posts response.

        Used by:

        1. Send button

        2. Sparkle button
        """

        try:

            _logger.info(
                "AI Prompt : %s",
                prompt,
            )

            ai = AIService()

            response = ai.ask(prompt)

            _logger.info("AI Formatted Response: %s", response)

            if not response:
                return

            self._post_ai_message(response)

        except Exception:

            _logger.exception(
                "AI Error"
            )

    # ==========================================================
    # Post Message
    # ==========================================================

    def _post_ai_message(
        self,
        response,
    ):
        response = markdown.markdown(response)
        odoobot = self.env.ref(
            "base.partner_root"
        )

        self.with_context(
            ai_reply=True
        ).message_post(
            author_id=odoobot.id,
            body=Markup(response),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    def _post_user_message(self, prompt):

        return self.with_context(
            ai_reply=True,
        ).message_post(
            body=prompt,
            author_id=self.env.user.partner_id.id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    # ==========================================================
    # Sparkle Button API
    # ==========================================================

    @api.model
    def generate_ai_reply(
        self,
        channel_id,
        prompt,
    ):
        """
        Called from the OWL Sparkle button.

        Parameters
        ----------
        channel_id : int
            Current discuss channel.

        prompt : str
            User typed message.

        Returns
        -------
        bool
        """

        _logger.info("=" * 80)
        _logger.info("Sparkle Button Clicked")
        _logger.info("Channel ID : %s", channel_id)
        _logger.info("Prompt     : %s", prompt)

        if not prompt:
            return False

        channel = self.browse(channel_id)

        if not channel.exists():
            _logger.warning(
                "Discuss Channel not found."
            )
            return False

        channel._post_user_message(prompt)
        channel._ask_ai(prompt)

        return True