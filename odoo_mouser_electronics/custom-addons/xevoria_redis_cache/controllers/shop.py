import logging

from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

from ..services.user_session_cache import UserSessionCache
from ..services.redis_config import RedisConfig


_logger = logging.getLogger(__name__)


class WebsiteSaleRedis(WebsiteSale):

    # ---------------------------------------------------------
    # User Session Cache
    # ---------------------------------------------------------

    def _load_user_session(self):
        """
        Load user session from Redis.

        If cache doesn't exist, create it.
        """

        if request.env.user._is_public():
            return None

        if not RedisConfig.redis_enabled(request.env):
            _logger.info(
                "Redis is disabled, skipping user session cache"
            )
            return None

        session_cache = UserSessionCache()

        session = session_cache.get_or_create(
            request.env.user
        )

        return session