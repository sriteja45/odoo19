import logging


_logger = logging.getLogger(__name__)


class RedisConfig:

    # ---------------------------------------------------------
    # GLOBAL REDIS
    # ---------------------------------------------------------

    @staticmethod
    def redis_enabled(env):
        val = (
            env["ir.config_parameter"]
            .sudo()
            .get_param(
                "xevoria_redis_cache.redis_cache_enabled",
                default="False",
            )
        )
        return str(val).strip().lower() in ("true", "1", "t", "yes")

    # ---------------------------------------------------------
    # WEBSITE CACHE
    # ---------------------------------------------------------

    @staticmethod
    def website_enabled(env):

        if not RedisConfig.redis_enabled(env):
            return False

        return (
            env["ir.config_parameter"]
            .sudo()
            .get_param(
                "xevoria_redis_cache.website_cache_enabled",
                default="False",
            )
            == "True"
        )

    # ---------------------------------------------------------
    # POS CACHE
    # ---------------------------------------------------------

    @staticmethod
    def pos_enabled(env):

        if not RedisConfig.redis_enabled(env):
            return False

        return (
            env["ir.config_parameter"]
            .sudo()
            .get_param(
                "xevoria_redis_cache.pos_cache_enabled",
                default="False",
            )
            == "True"
        )

    # ---------------------------------------------------------
    # DYNAMIC MODEL CACHE
    # ---------------------------------------------------------

    @classmethod
    def get_enabled_models(cls, env):
        """
        Get the set of technical model names enabled for Redis caching.
        Reads from ir.config_parameter (which Odoo caches in memory).
        """
        if not cls.redis_enabled(env):
            return set()

        param = env["ir.config_parameter"].sudo()
        cached_names = param.get_param(
            "xevoria_redis_cache.redis_cached_model_names",
            default="",
        )

        # Fallback / sync from model IDs if names parameter not yet set
        if not cached_names:
            model_ids = param.get_param(
                "xevoria_redis_cache.redis_cache_model_ids",
                default="",
            )
            if not model_ids:
                return set()

            selected_ids = [
                int(mid.strip())
                for mid in model_ids.split(",")
                if mid.strip().isdigit()
            ]
            if not selected_ids:
                return set()

            models = env["ir.model"].sudo().browse(selected_ids).exists()
            cached_names = ",".join(models.mapped("model"))
            param.set_param(
                "xevoria_redis_cache.redis_cached_model_names",
                cached_names,
            )

        return {
            name.strip()
            for name in cached_names.split(",")
            if name.strip()
        }

    @classmethod
    def is_model_enabled(cls, env, model_name):
        return model_name in cls.get_enabled_models(env)