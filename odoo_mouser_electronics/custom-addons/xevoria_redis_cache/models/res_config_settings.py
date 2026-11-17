import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    redis_cache_enabled = fields.Boolean(
        string="Enable Redis Cache",
        config_parameter="xevoria_redis_cache.redis_cache_enabled",
    )

    redis_cache_model_ids = fields.Many2many(
        "ir.model",
        string="Cache Models",
    )

    website_cache_enabled = fields.Boolean(
        string="Enable Website Cache",
        config_parameter="xevoria_redis_cache.website_cache_enabled",
    )

    pos_cache_enabled = fields.Boolean(
        string="Enable POS Cache",
        config_parameter="xevoria_redis_cache.pos_cache_enabled",
    )

    def get_values(self):
        res = super().get_values()

        param = self.env["ir.config_parameter"].sudo()

        model_ids = param.get_param(
            "xevoria_redis_cache.redis_cache_model_ids",
            default="",
        )

        if model_ids:
            model_ids = [
                int(model_id)
                for model_id in model_ids.split(",")
                if model_id
            ]
        else:
            model_ids = []

        res.update(
            redis_cache_model_ids=[(6, 0, model_ids)]
        )

        return res

    def set_values(self):
        super().set_values()

        param = self.env["ir.config_parameter"].sudo()

        model_ids = ",".join(
            str(model.id)
            for model in self.redis_cache_model_ids
        )

        param.set_param(
            "xevoria_redis_cache.redis_cache_model_ids",
            model_ids,
        )

        model_names = ",".join(
            self.redis_cache_model_ids.mapped("model")
        )

        param.set_param(
            "xevoria_redis_cache.redis_cached_model_names",
            model_names,
        )

        _logger.info("==================================================")
        _logger.info("[REDIS CACHE SETTINGS SAVED] Master Switch: %s", self.redis_cache_enabled)
        _logger.info("[REDIS CACHE SETTINGS SAVED] Cached Models: %s", model_names)
        _logger.info("==================================================")