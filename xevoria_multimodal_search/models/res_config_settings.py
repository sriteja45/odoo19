# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # =========================================================================
    # EmbeddingGemma 2 Settings
    # =========================================================================
    multimodal_model_id = fields.Char(
        string="EmbeddingGemma 2 Model ID",
        config_parameter="multimodal.model_id",
        default="google/embeddinggemma-2",
        help="Hugging Face model identifier for EmbeddingGemma 2 multimodal embeddings.",
    )
    multimodal_mrl_dimension = fields.Selection(
        selection=[
            ("768", "768-d (Full Precision / Default)"),
            ("512", "512-d (MRL Truncated)"),
            ("256", "256-d (MRL Compact / High Speed)"),
        ],
        string="Embedding Dimension (MRL)",
        config_parameter="multimodal.mrl_dimension",
        default="768",
        help="EmbeddingGemma 2 natively supports Matryoshka Representation Learning (MRL) truncation to 256d or 512d.",
    )
    multimodal_device = fields.Selection(
        selection=[
            ("auto", "Auto Detect (CUDA GPU if available, else CPU)"),
            ("cpu", "CPU (Standard)"),
            ("cuda", "NVIDIA CUDA GPU"),
        ],
        string="Inference Device",
        config_parameter="multimodal.device",
        default="auto",
        help="Hardware execution device for EmbeddingGemma 2 inference.",
    )
    multimodal_pgvector_db_url = fields.Char(
        string="PgVector Database URL",
        config_parameter="multimodal.pgvector_db_url",
        default="postgresql+psycopg://odoo:odoo@localhost:5532/odoo",
        help="PostgreSQL connection string with pgvector support (optional; in-DB fallback is used if offline).",
    )
    multimodal_min_score = fields.Float(
        string="Minimum Match Confidence (%)",
        config_parameter="multimodal.min_score",
        default=25.0,
        help="Minimum similarity score required to display a product in search results.",
    )
    multimodal_max_results = fields.Integer(
        string="Max Search Results",
        config_parameter="multimodal.max_results",
        default=10,
        help="Maximum number of matched products to return.",
    )

    # =========================================================================
    # Backward Compatibility (Prevents OwlError on un-upgraded cached views)
    # =========================================================================
    multimodal_openrouter_api_key = fields.Char(
        string="OpenRouter API Key (Legacy)",
        config_parameter="multimodal.openrouter_api_key",
    )
    multimodal_search_type = fields.Selection(
        selection=[
            ("hybrid", "Hybrid"),
            ("vector", "Vector"),
            ("keyword", "Keyword"),
        ],
        string="Search Type (Legacy)",
        config_parameter="multimodal.search_type",
        default="hybrid",
    )
    multimodal_gemini_api_key = fields.Char(
        string="Gemini API Key (Legacy)",
        config_parameter="multimodal.gemini_api_key",
    )
    multimodal_groq_api_key = fields.Char(
        string="Groq API Key (Legacy)",
        config_parameter="multimodal.groq_api_key",
    )

    def action_batch_index_all_products(self):
        """
        Trigger batch indexing of unindexed products using EmbeddingGemma 2.
        """
        unindexed_count = self.env["product.template"].search_count([
            ("sale_ok", "=", True),
            ("is_multimodal_indexed", "=", False),
        ])
        batch_size = 20
        count = self.env["product.template"].action_batch_index_multimodal(limit=batch_size)
        remaining = max(0, unindexed_count - count)

        msg = f"Indexed {count} products with EmbeddingGemma 2."
        if remaining > 0:
            msg += f" {remaining} products remaining to index (click button again to index next batch)."
        else:
            msg += " All catalog products are now indexed!"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Batch Multimodal Indexing",
                "message": msg,
                "type": "success",
                "sticky": False,
            }
        }
