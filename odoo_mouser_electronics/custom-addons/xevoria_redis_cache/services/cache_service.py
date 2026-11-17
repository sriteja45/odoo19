import json
import logging

from .redis_client import RedisClient


_logger = logging.getLogger(__name__)


class CacheService:

    DEFAULT_TTL = 3600

    def __init__(self):
        self.client = RedisClient.get_client()

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get(self, key):
        if not self.client:
            return None

        try:
            value = self.client.get(key)

            if value:
                _logger.info(
                    "Redis HIT : %s",
                    key,
                )
                return json.loads(value)

            _logger.info(
                "Redis MISS : %s",
                key,
            )
            return None

        except Exception as ex:
            _logger.exception(
                "Redis GET failed: %s",
                ex,
            )
            return None

    # ---------------------------------------------------------
    # SET
    # ---------------------------------------------------------

    def set(self, key, value, ttl=None):

        if not self.client:
            return False

        try:
            ttl = ttl or self.DEFAULT_TTL

            serialized_value = json.dumps(
                value,
                default=str,
            )

            result = self.client.set(
                key,
                serialized_value,
                ex=ttl,
            )

            if result:
                _logger.info(
                    "Redis SET : %s",
                    key,
                )
                return True

            _logger.warning(
                "Redis SET returned False : %s",
                key,
            )
            return False

        except Exception as ex:
            _logger.exception(
                "Redis SET failed: %s",
                ex,
            )
            return False

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(self, key):

        if not self.client:
            return False

        try:
            self.client.delete(key)

            _logger.info(
                "Redis DELETE : %s",
                key,
            )

            return True

        except Exception as ex:
            _logger.exception(
                "Redis DELETE failed: %s",
                ex,
            )
            return False

    # ---------------------------------------------------------
    # DELETE PATTERN
    # ---------------------------------------------------------

    def delete_pattern(self, pattern):

        if not self.client:
            return False

        try:
            cursor = 0
            total_deleted = 0

            while True:

                cursor, keys = self.client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100,
                )

                if keys:
                    self.client.delete(*keys)
                    total_deleted += len(keys)

                if cursor == 0:
                    break

            _logger.info(
                "Redis DELETE PATTERN: %s (%s keys)",
                pattern,
                total_deleted,
            )

            return True

        except Exception as ex:
            _logger.exception(
                "Redis pattern delete failed: %s",
                ex,
            )
            return False

    # ---------------------------------------------------------
    # EXISTS
    # ---------------------------------------------------------

    def exists(self, key):

        if not self.client:
            return False

        try:
            return bool(
                self.client.exists(key)
            )

        except Exception as ex:
            _logger.exception(
                "Redis EXISTS failed: %s",
                ex,
            )
            return False

    # ---------------------------------------------------------
    # CLEAR
    # ---------------------------------------------------------

    def clear(self):

        if not self.client:
            return False

        try:
            self.client.flushdb()

            _logger.info(
                "Redis database cleared"
            )

            return True

        except Exception as ex:
            _logger.exception(
                "Redis CLEAR failed: %s",
                ex,
            )
            return False