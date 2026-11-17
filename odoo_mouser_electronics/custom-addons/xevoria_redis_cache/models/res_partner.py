import logging

from odoo import models

from ..services.user_session_cache import UserSessionCache

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):

        result = super().write(vals)

        cache = UserSessionCache()

        users = self.env["res.users"].search([
            ("partner_id", "in", self.ids)
        ])

        for user in users:

            cache.invalidate(user.id)

            _logger.info(
                "Partner Updated - Redis Session Cleared : %s",
                user.login,
            )

        return result