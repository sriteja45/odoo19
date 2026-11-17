# -*- coding: utf-8 -*-

import base64
import hashlib
import logging

from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)

# Extension -> mimetype for the 3D formats we serve.
MODEL_MIMETYPES = {
    'glb': 'model/gltf-binary',
    'gltf': 'model/gltf+json',
    'usdz': 'model/vnd.usdz+zip',
}
IMAGE_MIMETYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif',
}


class Product3DController(http.Controller):
    """Serve 3D models and poster images.

    Two things matter here and are easy to get wrong:

    1. Access control. The records are read with sudo() so that public
       visitors can fetch the binary, which means we must check publication
       ourselves - otherwise anyone can enumerate record ids and download the
       3D models of unpublished / draft products.
    2. Memory. A GLB can easily be 20-80 MB. Decoding the whole base64 blob
       into RAM on every request does not scale, so we stream straight from
       the filestore via ir.binary and let the browser cache with ETag /
       304 Not Modified.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_internal_user(self):
        return request.env.user.has_group('base.group_user')

    def _check_product_access(self, product_tmpl):
        """Public visitors may only reach published products.

        Internal users (backend preview, editors) always pass.
        """
        if not product_tmpl:
            raise NotFound()
        if self._is_internal_user():
            return
        # website_sale products expose is_published / website_published
        published = getattr(product_tmpl, 'is_published', None)
        if published is None:
            published = getattr(product_tmpl, 'website_published', False)
        if not published:
            raise NotFound()
        # Respect the current website when the product is website-restricted
        website = request.env['website'].get_current_website()
        product_website = product_tmpl.website_id
        if product_website and website and product_website.id != website.id:
            raise NotFound()

    def _template_of(self, record):
        """Return the product.template a served record belongs to."""
        if record._name == 'product.template':
            return record
        if record._name == 'product.product':
            return record.product_tmpl_id
        if record._name == 'product.3d.model':
            return record.product_tmpl_id
        return request.env['product.template']

    def _extension(self, filename, default='glb'):
        if filename and '.' in filename:
            return filename.rsplit('.', 1)[-1].lower()
        return default

    def _stream_binary(self, record, field_name, filename, mimetype):
        """Stream a binary field without loading it fully into memory.

        Falls back to an in-memory response only if ir.binary is not usable
        for this record (e.g. the field is not stored as an attachment).
        """
        try:
            stream = request.env['ir.binary']._get_stream_from(
                record.sudo(), field_name, filename=filename,
            )
            stream.mimetype = mimetype
            response = stream.get_response(
                as_attachment=False,
                immutable=False,
            )
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
        except Exception:  # pragma: no cover - defensive fallback
            _logger.debug(
                "website_product_3d: streaming failed for %s.%s, "
                "falling back to in-memory response",
                record._name, field_name, exc_info=True,
            )
            return self._inline_binary(record[field_name], filename, mimetype)

    def _inline_binary(self, data_b64, filename, mimetype):
        """Fallback: decode in memory, but still support ETag / 304."""
        raw = base64.b64decode(data_b64)
        etag = '"%s"' % hashlib.sha1(raw).hexdigest()
        if request.httprequest.headers.get('If-None-Match') == etag:
            return request.make_response('', headers=[('ETag', etag)], status=304)
        headers = [
            ('Content-Type', mimetype),
            ('Content-Length', str(len(raw))),
            ('Content-Disposition', f'inline; filename="{filename}"'),
            ('Cache-Control', 'public, max-age=3600'),
            ('ETag', etag),
            ('X-Content-Type-Options', 'nosniff'),
        ]
        return request.make_response(raw, headers=headers)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @http.route(
        '/website_product_3d/model/<string:model_name>/<int:record_id>/<string:field_name>',
        type='http', auth='public', website=True, sitemap=False,
    )
    def product_3d_model(self, model_name, record_id, field_name, **kwargs):
        """Serve supported public 3D binary fields and poster images."""
        allowed = {
            'product.template': {'product_3d_model', 'product_3d_poster'},
            'product.product': {'product_3d_model'},
            'product.3d.model': {'model_file'},
        }
        if model_name not in allowed or field_name not in allowed[model_name]:
            raise NotFound()

        record = request.env[model_name].sudo().browse(record_id).exists()
        if not record:
            raise NotFound()

        # Publication / website check before anything is served.
        self._check_product_access(self._template_of(record))

        if not record[field_name]:
            raise NotFound()

        # Filename handling
        if model_name == 'product.3d.model':
            filename = record.model_filename or 'model.glb'
        else:
            filename = record[f'{field_name}_filename'] or (
                'poster.jpg' if 'poster' in field_name else 'model.glb'
            )

        # Poster images
        if field_name == 'product_3d_poster':
            extension = self._extension(filename, default='jpg')
            mimetype = IMAGE_MIMETYPES.get(extension, 'image/jpeg')
            return self._stream_binary(record, field_name, filename, mimetype)

        # 3D models
        extension = self._extension(filename)
        if extension not in MODEL_MIMETYPES:
            raise NotFound()
        return self._stream_binary(
            record, field_name, filename, MODEL_MIMETYPES[extension],
        )

    @http.route(
        '/website_product_3d/default_model/<int:product_tmpl_id>',
        type='http', auth='user', website=True, sitemap=False,
    )
    def product_3d_default_model(self, product_tmpl_id, **kwargs):
        """Serve the default 3D model of a product.template.

        Used by the backend form preview only, hence auth='user'.
        Prefers the multi-model list (product.3d.model with is_default),
        then falls back to the legacy single Binary field.
        """
        product = request.env['product.template'].sudo().browse(product_tmpl_id).exists()
        if not product:
            raise NotFound()

        default_model = product._get_default_3d_model()
        if default_model and default_model.model_file:
            record, field_name = default_model, 'model_file'
            filename = default_model.model_filename or 'model.glb'
        elif product.product_3d_model:
            record, field_name = product, 'product_3d_model'
            filename = product.product_3d_model_filename or 'model.glb'
        else:
            raise NotFound()

        extension = self._extension(filename)
        if extension not in MODEL_MIMETYPES:
            raise NotFound()
        return self._stream_binary(
            record, field_name, filename, MODEL_MIMETYPES[extension],
        )
