# -*- coding: utf-8 -*-
import base64
import json
import logging
import mimetypes
from odoo import http
from odoo.http import request
from ..services.multimodal_service import MultimodalService

_logger = logging.getLogger(__name__)


class MultimodalSearchController(http.Controller):

    @http.route('/shop/multimodal/search', type='http', auth='public', methods=['POST'], csrf=False)
    def search_multimodal(self, **post):
        """
        Accepts uploaded product image, uploaded video file, video URL, or text query,
        and retrieves matching catalog products (along with their playable product videos)
        strictly from EmbeddingGemma 2 unified vectors stored in PgVector / xevoria.multimodal.embedding.
        """
        try:
            uploaded_file = request.httprequest.files.get('file') or post.get('file')
            media_type = (post.get('media_type') or request.httprequest.form.get('media_type') or '').lower()
            text_query = (post.get('text_query') or request.httprequest.form.get('text_query') or '').strip()
            video_url = (post.get('video_url') or request.httprequest.form.get('video_url') or '').strip()

            filename = getattr(uploaded_file, 'filename', '') or ""
            content_type = getattr(uploaded_file, 'content_type', '') or ""

            if not media_type:
                if video_url or content_type.startswith('video/') or filename.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mkv')):
                    media_type = 'video'
                elif uploaded_file:
                    media_type = 'image'
                else:
                    media_type = 'text'

            file_bytes = None
            if uploaded_file:
                if hasattr(uploaded_file, 'read'):
                    file_bytes = uploaded_file.read()
                elif isinstance(uploaded_file, (bytes, bytearray)):
                    file_bytes = bytes(uploaded_file)

            max_results = int(request.env['ir.config_parameter'].sudo().get_param(
                'multimodal.max_results', 10
            ))

            service = MultimodalService(request.env)

            is_video = (
                (media_type == 'video')
                or bool(video_url)
                or content_type.startswith('video/')
                or filename.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mkv'))
            )
            results, extracted_info = service.search(
                text_query=text_query if (not file_bytes and not video_url) else None,
                image_bytes=file_bytes if (file_bytes and not is_video) else None,
                video_bytes=file_bytes if (file_bytes and is_video) else None,
                video_url=video_url if is_video and video_url else None,
                limit=max_results,
            )

            return self._json_response({
                "success": True,
                "media_type": "video" if is_video else media_type,
                "extracted_query": extracted_info or text_query or video_url or filename,
                "total": len(results),
                "results": results,
            })

        except Exception as e:
            _logger.exception("Error during multimodal search execution: %s", e)
            return self._json_response({
                "success": False,
                "error": str(e)
            }, status=500)

    @http.route('/shop/multimodal/product_video/<int:product_id>', type='http', auth='public', methods=['GET'])
    def stream_product_video(self, product_id, **kw):
        """
        Streams an uploaded product video (`product.multimodal_video_file` or a `video/*` attachment)
        so matched product cards in the search modal can play the product video directly.
        """
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()

        video_bytes = None
        mime_type = "video/mp4"

        if getattr(product, "multimodal_video_file", False):
            raw_data = product.multimodal_video_file
            video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, (str, bytes)) else None
            fname = getattr(product, "multimodal_video_filename", "") or "product_video.mp4"
            guessed_mime, _ = mimetypes.guess_type(fname)
            if guessed_mime and guessed_mime.startswith("video/"):
                mime_type = guessed_mime
        else:
            att = request.env["ir.attachment"].sudo().search([
                ("res_model", "=", "product.template"),
                ("res_id", "=", product.id),
                ("mimetype", "ilike", "video/"),
            ], limit=1)
            if att and att.datas:
                video_bytes = base64.b64decode(att.datas)
                mime_type = att.mimetype or "video/mp4"

        if not video_bytes:
            return request.not_found()

        headers = [
            ('Content-Type', mime_type),
            ('Content-Length', str(len(video_bytes))),
            ('Accept-Ranges', 'bytes'),
            ('Cache-Control', 'public, max-age=3600'),
        ]
        return request.make_response(video_bytes, headers=headers)

    @http.route('/shop/multimodal/status', type='jsonrpc', auth='public')
    def get_status(self):
        product_count = request.env['product.template'].sudo().search_count([('sale_ok', '=', True)])
        model_id = request.env['ir.config_parameter'].sudo().get_param(
            'multimodal.model_id', 'google/embeddinggemma-2'
        )
        mrl_dim = request.env['ir.config_parameter'].sudo().get_param(
            'multimodal.mrl_dimension', '768'
        )
        return {
            "total_products": product_count,
            "architecture": "EmbeddingGemma 2",
            "model": model_id,
            "dimension": int(mrl_dim),
            "modalities": ["text", "image", "video"],
        }

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*'),
            ],
            status=status
        )
