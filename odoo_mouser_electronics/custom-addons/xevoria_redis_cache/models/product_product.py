import logging

from odoo import api, models

from ..services.pos_cache import PosCache
from ..services.redis_config import RedisConfig

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_search_read(self, data, config):
        """
        Intercept POS Product loading.

        Flow

            POS
              ↓
        Redis Lookup
              ↓
          HIT / MISS
              ↓
        Return Products
        """

        cache = PosCache()

        if not RedisConfig.is_model_enabled(
            self.env,
            self._name,
        ):
            _logger.info(
                "Redis cache is not enabled for model: %s",
                self._name,
            )
            return super()._load_pos_data_search_read(
                data,
                config,
            )

        if not RedisConfig.pos_enabled(self.env):
            _logger.info("POS cache is disabled, skipping POS cache")
            return super()._load_pos_data_search_read(
                data,
                config,
            )

        company_id = config.company_id.id
        config_id = config.id

        pricelist_id = (
            config.pricelist_id.id
            if config.pricelist_id
            else None
        )

        lang = self.env.context.get(
            "lang",
            "en_US",
        )

        try:

            # -----------------------------------
            # Redis Lookup
            # -----------------------------------

            cached_products = cache.get_products(
                company_id=company_id,
                config_id=config_id,
                pricelist_id=pricelist_id,
                lang=lang,
            )

            if cached_products:

                _logger.info(
                    "Loaded POS Products from Redis."
                )

                return cached_products

            # -----------------------------------
            # Database Lookup
            # -----------------------------------

            _logger.info(
                "Loading POS Products from Database."
            )

            products = super()._load_pos_data_search_read(
                data,
                config,
            )

            # -----------------------------------
            # Cache Result
            # -----------------------------------

            cache.set_products(
                company_id=company_id,
                config_id=config_id,
                pricelist_id=pricelist_id,
                lang=lang,
                products=products,
            )

            return products

        except Exception as ex:

            _logger.exception(
                "POS Redis Error : %s",
                ex,
            )

            return super()._load_pos_data_search_read(
                data,
                config,
            )
    
    # ==========================================================
    # Cache Invalidation
    # ==========================================================

    def _invalidate_pos_cache(self):
        """
        Clear POS Redis cache for affected companies.
        """

        cache = PosCache()

        companies = self.mapped("company_id")

        if companies:

            for company in companies:

                cache.invalidate_products(
                    company_id=company.id
                )

        else:

            cache.invalidate_products()

    # ==========================================================
    # CREATE
    # ==========================================================

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        records._invalidate_pos_cache()

        return records

    # ==========================================================
    # WRITE
    # ==========================================================

    def write(self, vals):

        result = super().write(vals)

        self._invalidate_pos_cache()

        return result

    # ==========================================================
    # UNLINK
    # ==========================================================

    def unlink(self):

        self._invalidate_pos_cache()

        return super().unlink()