import logging

from .cache_service import CacheService
from .redis_config import RedisConfig


_logger = logging.getLogger(__name__)


class ModelCacheService:

    DEFAULT_TTL = 3600

    def __init__(self, env):
        self.env = env
        self.cache = CacheService()

    # ---------------------------------------------------------
    # CHECK MODEL
    # ---------------------------------------------------------

    def is_enabled(self, model_name):

        return RedisConfig.is_model_enabled(
            self.env,
            model_name,
        )

    # ---------------------------------------------------------
    # REDIS KEY
    # ---------------------------------------------------------

    def _key(self, model_name, record_id):

        return f"odoo:model:{model_name}:{record_id}"

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get(self, model_name, record_id):

        if not self.is_enabled(model_name):
            return None

        key = self._key(
            model_name,
            record_id,
        )

        value = self.cache.get(key)

        if value is not None:

            _logger.info(
                "MODEL CACHE HIT: model=%s id=%s",
                model_name,
                record_id,
            )

        else:

            _logger.info(
                "MODEL CACHE MISS: model=%s id=%s",
                model_name,
                record_id,
            )

        return value

    # ---------------------------------------------------------
    # SET
    # ---------------------------------------------------------

    def set(
        self,
        model_name,
        record_id,
        values,
        ttl=None,
    ):

        if not self.is_enabled(model_name):
            return False

        key = self._key(
            model_name,
            record_id,
        )

        success = self.cache.set(
            key,
            values,
            ttl=ttl or self.DEFAULT_TTL,
        )

        if success:

            _logger.info(
                "MODEL CACHE SET: model=%s id=%s",
                model_name,
                record_id,
            )

        else:

            _logger.warning(
                "MODEL CACHE SET FAILED: model=%s id=%s",
                model_name,
                record_id,
            )

        return success

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(self, model_name, record_id):

        if not self.is_enabled(model_name):
            return False

        key = self._key(
            model_name,
            record_id,
        )

        success = self.cache.delete(key)

        if success:

            _logger.info(
                "MODEL CACHE DELETE: model=%s id=%s",
                model_name,
                record_id,
            )

        return success

    # ---------------------------------------------------------
    # DELETE MODEL CACHE
    # ---------------------------------------------------------

    def delete_model(self, model_name):

        if not self.is_enabled(model_name):
            return False

        pattern = f"odoo:model:{model_name}:*"

        success = self.cache.delete_pattern(
            pattern
        )

        if success:

            _logger.info(
                "MODEL CACHE CLEARED: model=%s",
                model_name,
            )

        return success