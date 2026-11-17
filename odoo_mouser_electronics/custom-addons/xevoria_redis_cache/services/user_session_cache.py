import logging

from odoo.http import request

from .cache_service import CacheService

_logger = logging.getLogger(__name__)


class UserSessionCache:

    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self):
        self.cache = CacheService()

    def _key(self, user_id):
        """
        Redis Key

        session:user:7
        """
        return f"session:user:{user_id}"

    def get(self, user_id):
        """
        Get cached session data.
        """
        return self.cache.get(self._key(user_id))

    def set(self, user):
        """
        Cache frequently accessed user information.
        """

        data = {
            "uid": user.id,
            "partner_id": user.partner_id.id,
            "company_id": user.company_id.id,
            "website_id": request.website.id if request else None,
            "lang": user.lang,
            "tz": user.tz,
            "groups": user.group_ids.ids,
        }

        self.cache.set(
            self._key(user.id),
            data,
            ttl=self.DEFAULT_TTL,
        )

        _logger.info(
            "User session cached for User %s",
            user.id,
        )

        return data

    def get_or_create(self, user):
        """
        Return cached session.
        If unavailable, build it and cache it.
        """

        cached = self.get(user.id)

        if cached:
            _logger.info(
                "Redis Session HIT : User %s",
                user.id,
            )
            return cached

        _logger.info(
            "Redis Session MISS : User %s",
            user.id,
        )

        return self.set(user)

    def invalidate(self, user_id):
        """
        Remove one user's session cache.
        """

        self.cache.delete(
            self._key(user_id)
        )

        _logger.info(
            "Redis Session Cleared : User %s",
            user_id,
        )

    def exists(self, user_id):
        return self.cache.exists(
            self._key(user_id)
        )