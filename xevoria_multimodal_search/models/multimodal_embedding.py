# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, fields, models
from ..services.multimodal_service import MultimodalService

_logger = logging.getLogger(__name__)


class XevoriaMultimodalEmbedding(models.Model):
    _name = "xevoria.multimodal.embedding"
    _description = "Multimodal Vector Embedding Index (EmbeddingGemma 2)"
    _order = "id desc"

    name = fields.Char(string="Label / Title", required=True)
    media_type = fields.Selection(
        selection=[
            ("image", "Image (Visual Embedding)"),
            ("text", "Text / Specification"),
            ("video", "Video (Visual Sequence Embedding)"),
            ("audio", "Audio (Legacy)"),
        ],
        string="Media Modality",
        required=True,
        default="image",
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_name = fields.Char(
        related="product_tmpl_id.name",
        string="Product Name",
        readonly=True,
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Media File",
        ondelete="set null",
    )
    video_url = fields.Char(
        string="Video URL",
        help="Direct or embedded video URL associated with this product embedding.",
    )
    description = fields.Text(
        string="Extracted Description / Text Document",
        help="Indexed document text formatted with task prefix, e.g., 'title: ... | text: ...'",
    )
    dimension = fields.Integer(
        string="Vector Dimensions",
        default=768,
        help="Embedding dimension (768 for EmbeddingGemma 2, or truncated 256/512 via MRL).",
    )
    embedding_json = fields.Text(
        string="Vector Embedding (JSON Array)",
        help="EmbeddingGemma 2 float vector stored in database.",
    )
    similarity_score = fields.Float(
        string="Match Score",
        compute="_compute_dummy",
        help="Temporary similarity percentage for search results.",
    )

    def _compute_dummy(self):
        for rec in self:
            rec.similarity_score = 0.0

    # =========================================================================
    # Vector Search Engine (Embedding Retrieval)
    # =========================================================================

    @api.model
    def search_vector(self, query_vector, media_types=None, limit=10, min_similarity=0.25):
        """
        Search indexed database records by vector similarity (Cosine Distance).
        EmbeddingGemma 2 maps text, images, and videos into the exact same 768-d space.
        Returns a list of dictionaries with matching product details, similarity scores,
        and matched product video URLs.
        """
        if not query_vector:
            return []

        domain = []
        if media_types:
            domain.append(("media_type", "in", media_types))

        records = self.search(domain)
        if not records:
            return []

        scored_products = {}
        service = MultimodalService(self.env)

        for rec in records:
            if not rec.embedding_json or not rec.product_tmpl_id:
                continue

            try:
                doc_vec = json.loads(rec.embedding_json)
            except Exception:
                continue

            score = service.cosine_similarity(query_vector, doc_vec)
            if score < min_similarity:
                continue

            product = rec.product_tmpl_id
            product_id = product.id
            score_pct = round(score * 100, 1)

            if product_id not in scored_products or score_pct > scored_products[product_id]["score"]:
                scored_products[product_id] = service._build_product_result_dict(
                    product,
                    score_pct=score_pct,
                    media_type=rec.media_type,
                    source_prefix="EmbeddingGemma 2",
                )

        results = sorted(scored_products.values(), key=lambda x: x["score"], reverse=True)
        return results[:limit]
