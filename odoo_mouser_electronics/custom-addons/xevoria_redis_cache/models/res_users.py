import logging

from odoo import models

from ..services.user_session_cache import UserSessionCache

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _invalidate_user_session(self):
        """
        Remove Redis session cache for users.
        """

        cache = UserSessionCache()

        for user in self:
            cache.invalidate(user.id)

            _logger.info(
                "Redis User Session Cleared : %s",
                user.login,
            )

    def write(self, vals):

        result = super().write(vals)

        self._invalidate_user_session()

        return result

    def unlink(self):

        self._invalidate_user_session()

        return super().unlink()