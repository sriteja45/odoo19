import logging

from odoo import api, models

from ..services.cache_service import CacheService

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ==========================================================
    # CACHE INVALIDATION
    # ==========================================================

    def _clear_shop_cache(self):
        """
        Remove all cached shop/product data from Redis.
        """

        cache = CacheService()

        # Redis connection available lekapothe
        # cache clearing skip cheyyali.
        if not cache.client:
            _logger.info(
                "Redis client is not available, skipping cache clear."
            )
            return

        try:
            client = cache.client

            patterns = [
                "shop:*",
                "product:*",
                "category:*",
                "featured_products",
                "new_products",
            ]

            total_deleted = 0

            for pattern in patterns:

                cursor = 0

                while True:

                    cursor, keys = client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100,
                    )

                    if keys:
                        client.delete(*keys)
                        total_deleted += len(keys)

                    if cursor == 0:
                        break

            _logger.info(
                "Redis Cache Cleared (%s keys)",
                total_deleted,
            )

        except Exception as ex:

            _logger.exception(
                "Redis cache clear failed: %s",
                ex,
            )

    # ==========================================================
    # CREATE
    # ==========================================================

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create product templates and clear related Redis cache.
        """

        records = super().create(vals_list)

        records._clear_shop_cache()

        return records

    # ==========================================================
    # WRITE
    # ==========================================================

    def write(self, vals):
        """
        Update product templates and clear related Redis cache.
        """

        result = super().write(vals)

        self._clear_shop_cache()

        return result

    # ==========================================================
    # UNLINK
    # ==========================================================

    def unlink(self):
        """
        Delete product templates and clear related Redis cache.
        """

        self._clear_shop_cache()

        return super().unlink()