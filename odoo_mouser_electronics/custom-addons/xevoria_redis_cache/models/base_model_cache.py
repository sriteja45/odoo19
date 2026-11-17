import hashlib
import json
import logging

from odoo import api, models

from ..services.cache_service import CacheService
from ..services.redis_config import RedisConfig


_logger = logging.getLogger(__name__)


class BaseModelRedisCache(models.AbstractModel):

    _inherit = "base"

    # ---------------------------------------------------------
    # MODELS EXCLUDED FROM UNIVERSAL REDIS CACHE
    # ---------------------------------------------------------

    REDIS_CACHE_EXCLUDED_MODELS = {
        "ir.config_parameter",
        "ir.model",
        "ir.model.fields",
        "ir.model.data",
        "ir.attachment",
        "res.config.settings",
        "bus.bus",
    }

    # ---------------------------------------------------------
    # REDIS CACHE HELPERS
    # ---------------------------------------------------------

    def _redis_cache(self):
        return CacheService()

    def _redis_enabled(self):
        """
        Check whether Redis is globally enabled and whether
        the current model is selected in Redis Cache settings.
        """
        if self._abstract:
            return False

        if self._name in self.REDIS_CACHE_EXCLUDED_MODELS:
            return False

        return RedisConfig.is_model_enabled(
            self.env,
            self._name,
        )

    def _make_redis_key(self, method_name, *args, **kwargs):
        """
        Generate a deterministic Redis key based on model, method,
        company, language, and method arguments.
        """
        payload = {
            "model": self._name,
            "method": method_name,
            "company_id": self.env.company.id if hasattr(self.env, "company") else None,
            "lang": self.env.context.get("lang"),
            "args": args,
            "kwargs": kwargs,
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        sig = hashlib.md5(raw.encode()).hexdigest()
        return f"odoo:model:{self._name}:{method_name}:{sig}"

    def _clear_model_redis_cache(self):
        """
        Invalidate all Redis cache entries for this model.
        """
        pattern = f"odoo:model:{self._name}:*"
        self._redis_cache().delete_pattern(pattern)
        _logger.info("REDIS CACHE INVALIDATED: model=%s", self._name)

    # ---------------------------------------------------------
    # READ (Used by Form Views and Record-level reads)
    # ---------------------------------------------------------

    def read(self, fields=None, load="_classic_read"):
        """
        Intercept direct read requests on specific record IDs.
        """
        if not self._redis_enabled() or not self.ids:
            return super().read(fields=fields, load=load)

        key = self._make_redis_key("read", sorted(self.ids), fields=fields, load=load)
        cache = self._redis_cache()
        cached = cache.get(key)
        if cached is not None:
            _logger.info("REDIS CACHE HIT: model=%s (read)", self._name)
            return cached

        res = super().read(fields=fields, load=load)
        cache.set(key, res)
        _logger.info("REDIS CACHE MISS: model=%s (read cached)", self._name)
        return res

    # ---------------------------------------------------------
    # CREATE / WRITE / UNLINK
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._redis_enabled():
            self._clear_model_redis_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self._redis_enabled():
            self._clear_model_redis_cache()
        return res

    def unlink(self):
        res = super().unlink()
        if self._redis_enabled():
            self._clear_model_redis_cache()
        return res