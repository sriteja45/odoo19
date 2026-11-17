from odoo import models

from ..services.cache_service import CacheService
from ..services.redis_config import RedisConfig


class RedisModelCache(models.AbstractModel):
    _name = "xevoria.redis.model.cache"
    _description = "Generic Redis Model Cache"

    def get_cache(self, model_name, record_id):
        if not RedisConfig.is_model_enabled(self.env, model_name):
            return None

        cache = CacheService()

        key = f"{model_name}:{record_id}"

        return cache.get(key)

    def set_cache(self, model_name, record_id, value, ttl=300):
        if not RedisConfig.is_model_enabled(self.env, model_name):
            return

        cache = CacheService()

        key = f"{model_name}:{record_id}"

        cache.set(key, value, ttl=ttl)

    def delete_cache(self, model_name, record_id):
        cache = CacheService()

        key = f"{model_name}:{record_id}"

        cache.delete(key)