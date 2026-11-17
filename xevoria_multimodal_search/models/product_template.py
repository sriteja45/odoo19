# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from ..services.multimodal_service import MultimodalService

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_multimodal_indexed = fields.Boolean(
        string="Indexed in Vector Store",
        default=False,
        copy=False,
        help="Flag indicating whether this product has EmbeddingGemma 2 vectors generated.",
    )
    multimodal_video_url = fields.Char(
        string="Product Video URL",
        copy=False,
        help="Direct video URL (.mp4, .webm) or YouTube/Vimeo link for EmbeddingGemma 2 video indexing and search display.",
    )
    multimodal_video_file = fields.Binary(
        string="Upload Product Video",
        attachment=True,
        copy=False,
        help="Upload a product video file (MP4, WebM, MOV) to generate 768-d video embeddings and display in search results.",
    )
    multimodal_video_filename = fields.Char(
        string="Video Filename",
        copy=False,
    )

    def action_generate_multimodal_embeddings(self):
        """
        Index one or more products (text, image, and video) using EmbeddingGemma 2.
        Supports both single-product button clicks and multi-record Action menu selections,
        committing progress after each product when indexing multiple records.
        """
        service = MultimodalService(self.env)
        total_records = len(self)
        indexed_count = 0
        last_error = None

        for idx, product in enumerate(self, start=1):
            try:
                _logger.info(
                    "Indexing product [%d/%d]: id=%s (%s)...",
                    idx, total_records, product.id, product.name,
                )
                service.index_product(product)
                product.is_multimodal_indexed = True
                indexed_count += 1
                if total_records > 1:
                    self.env.cr.commit()
            except Exception as e:
                last_error = e
                _logger.exception("Failed to index product %s: %s", product.name, e)
                if total_records > 1:
                    self.env.cr.rollback()

        if indexed_count == 0 and last_error:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Indexing Failed",
                    "message": str(last_error),
                    "type": "danger",
                    "sticky": True,
                }
            }

        msg = (
            f"'{self[0].name}' (Text, Image & Video) was successfully embedded with EmbeddingGemma 2 and indexed."
            if total_records == 1
            else f"Successfully indexed {indexed_count} of {total_records} selected products with EmbeddingGemma 2."
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Product Indexed" if total_records == 1 else "Batch Indexing Complete",
                "message": msg,
                "type": "success",
                "sticky": False,
            }
        }

    @api.model
    def action_batch_index_multimodal(self, limit=20):
        """
        Batch index products in chunks (prioritizing unindexed products).
        Commits after each product so progress is saved incrementally.
        """
        products = self.search([
            ("sale_ok", "=", True),
            ("is_multimodal_indexed", "=", False),
        ], limit=limit)

        if not products:
            products = self.search([("sale_ok", "=", True)], limit=limit)

        service = MultimodalService(self.env)
        total = 0
        count_all = len(products)
        for idx, p in enumerate(products, start=1):
            try:
                _logger.info("Batch indexing [%d/%d]: id=%s (%s)...", idx, count_all, p.id, p.name)
                service.index_product(p)
                p.is_multimodal_indexed = True
                self.env.cr.commit()
                total += 1
            except Exception as e:
                _logger.error("Batch index error for product %s: %s", p.name, e)
                self.env.cr.rollback()
        return total
