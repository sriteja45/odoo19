# -*- coding: utf-8 -*-
import base64
import logging

from odoo import http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# Keep in sync with rating.rating._WSRE_* constants
_ALLOWED_MIMETYPES = frozenset({
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/webm', 'video/quicktime',
})
_MAX_SIZE = 10 * 1024 * 1024  # 10 MiB
_MAX_FILES = 5


class ReviewVoteController(http.Controller):

    @http.route(['/website_sale/review/vote'], type='jsonrpc', auth='user', methods=['POST'], website=True)
    def vote_review(self, rating_id, vote_type):
        """Cast/toggle a helpful/unhelpful vote on an existing review.

        This is a new, narrowly-scoped route (there is nothing in core to
        extend for voting - see models/rating_vote.py). It deliberately
        does NOT touch /website/rating/comment or any other existing
        rating route from 'rating'/'portal_rating'.
        """
        try:
            result = request.env['rating.vote'].set_vote(rating_id, vote_type)
        except UserError as e:
            return {'error': str(e)}
        return result

    @http.route(
        ['/website_sale/review/upload'],
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
        csrf=True,
    )
    def upload_review_media(self, **kwargs):
        """Multipart upload endpoint for review photos/videos.

        JSON-RPC cannot carry binary payloads, so the composer posts
        files here first, receives attachment ids, then includes those
        ids in the subsequent message_post (review_attachment_ids).

        Returns JSON: {ok: true, attachments: [{id, name, mimetype, url, is_image, is_video}, ...]}
        or {ok: false, error: "..."}.
        """
        files = request.httprequest.files.getlist('ufile') or request.httprequest.files.getlist('files')
        if not files:
            single = request.httprequest.files.get('ufile') or request.httprequest.files.get('file')
            files = [single] if single else []

        if not files:
            return request.make_json_response({'ok': False, 'error': 'No files received.'})

        if len(files) > _MAX_FILES:
            return request.make_json_response({
                'ok': False,
                'error': 'A review may include at most %s media files.' % _MAX_FILES,
            })

        Attachment = request.env['ir.attachment'].sudo()
        results = []
        try:
            for f in files:
                if not f or not f.filename:
                    continue
                raw = f.read()
                if len(raw) > _MAX_SIZE:
                    return request.make_json_response({
                        'ok': False,
                        'error': "File '%s' is too large. Maximum size is 10 MiB." % f.filename,
                    })
                mimetype = (f.content_type or '').split(';')[0].strip().lower()
                if mimetype not in _ALLOWED_MIMETYPES:
                    return request.make_json_response({
                        'ok': False,
                        'error': "Unsupported type '%s' for '%s'." % (mimetype or 'unknown', f.filename),
                    })
                att = Attachment.create({
                    'name': f.filename,
                    'datas': base64.b64encode(raw),
                    'res_model': 'rating.rating',
                    'res_id': 0,
                    'public': False,
                    'mimetype': mimetype,
                })
                att.generate_access_token()
                is_image = mimetype.startswith('image/')
                is_video = mimetype.startswith('video/')
                results.append({
                    'id': att.id,
                    'name': att.name,
                    'mimetype': mimetype,
                    'is_image': is_image,
                    'is_video': is_video,
                    'url': '/web/content/%s?access_token=%s' % (att.id, att.access_token),
                    'access_token': att.access_token,
                })
        except (AccessError, ValidationError, UserError) as e:
            _logger.warning("Review media upload failed: %s", e)
            return request.make_json_response({'ok': False, 'error': str(e)})
        except Exception:
            _logger.exception("Unexpected error during review media upload")
            return request.make_json_response({'ok': False, 'error': 'Upload failed.'})

        return request.make_json_response({'ok': True, 'attachments': results})

    @http.route(
        ['/website_sale/review/filter'],
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def filter_reviews(self, product_tmpl_id, product_id=None, variant_only=False):
        """Return review message ids + light stats for the product page.

        Used by the "This variant only" toggle. When variant_only is true
        and product_id is set, domain is narrowed via
        product.template._rating_domain_for_variant().

        Response:
            {
              ok: true,
              message_ids: [int, ...],
              stats: {count, avg, product_id},
              variant_only: bool,
            }
        """
        try:
            tmpl_id = int(product_tmpl_id)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'Invalid product template.'}

        Product = request.env['product.template'].sudo().browse(tmpl_id)
        if not Product.exists():
            return {'ok': False, 'error': 'Product not found.'}

        pid = None
        if product_id:
            try:
                pid = int(product_id)
            except (TypeError, ValueError):
                pid = None

        from odoo.fields import Domain
        if variant_only and pid:
            domain = Product._rating_domain_for_variant(pid)
        else:
            domain = Product._rating_domain() & Domain('res_id', '=', Product.id)

        Rating = request.env['rating.rating'].sudo()
        ratings = Rating.search(domain, order='create_date desc')
        message_ids = ratings.mapped('message_id').ids
        stats = Product.get_variant_review_stats(pid if (variant_only and pid) else None)

        return {
            'ok': True,
            'message_ids': message_ids,
            'rating_ids': ratings.ids,
            'stats': stats,
            'variant_only': bool(variant_only and pid),
            'product_id': pid or False,
            'product_tmpl_id': tmpl_id,
        }


    # ------------------------------------------------------------------
    # Phase 3 — Q&A Engine
    # ------------------------------------------------------------------

    @http.route(
        ['/website_sale/question/ask'],
        type='jsonrpc',
        auth='user',
        methods=['POST'],
        website=True,
    )
    def ask_question(self, product_tmpl_id, name, body='', product_id=None, is_anonymous=False):
        """Post a new question on a product template."""
        try:
            tmpl_id = int(product_tmpl_id)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'Invalid product.'}
        Product = request.env['product.template'].sudo().browse(tmpl_id)
        if not Product.exists():
            return {'ok': False, 'error': 'Product not found.'}
        name = (name or '').strip()
        if len(name) < 5:
            return {'ok': False, 'error': 'Please write a question of at least 5 characters.'}
        vals = {
            'name': name,
            'body': (body or '').strip() or False,
            'product_tmpl_id': tmpl_id,
            'partner_id': request.env.user.partner_id.id,
            'is_anonymous': bool(is_anonymous),
        }
        if product_id:
            try:
                vals['product_id'] = int(product_id)
            except (TypeError, ValueError):
                pass
        try:
            question = request.env['product.question'].sudo().create(vals)
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        return {'ok': True, 'question': question.to_public_dict()}

    @http.route(
        ['/website_sale/question/answer'],
        type='jsonrpc',
        auth='user',
        methods=['POST'],
        website=True,
    )
    def answer_question(self, question_id, body):
        """Post an answer to an existing question."""
        try:
            qid = int(question_id)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'Invalid question.'}
        Question = request.env['product.question'].sudo().browse(qid)
        if not Question.exists() or not Question.website_published:
            return {'ok': False, 'error': 'Question not found.'}
        body = (body or '').strip()
        if len(body) < 2:
            return {'ok': False, 'error': 'Answer is too short.'}
        try:
            answer = request.env['product.answer'].sudo().create({
                'question_id': qid,
                'body': body,
                'partner_id': request.env.user.partner_id.id,
            })
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        return {'ok': True, 'answer': answer.to_public_dict()}

    @http.route(
        ['/website_sale/question/upvote'],
        type='jsonrpc',
        auth='user',
        methods=['POST'],
        website=True,
    )
    def upvote_question(self, question_id=None, answer_id=None):
        """Toggle upvote on a question or an answer."""
        try:
            if question_id:
                record = request.env['product.question'].sudo().browse(int(question_id))
                if not record.exists():
                    return {'ok': False, 'error': 'Question not found.'}
                result = record.upvote()
                return {'ok': True, **result}
            if answer_id:
                record = request.env['product.answer'].sudo().browse(int(answer_id))
                if not record.exists():
                    return {'ok': False, 'error': 'Answer not found.'}
                result = record.upvote()
                return {'ok': True, **result}
        except UserError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        return {'ok': False, 'error': 'Provide question_id or answer_id.'}

    @http.route(
        ['/website_sale/question/list'],
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def list_questions(self, product_tmpl_id, limit=20, offset=0):
        """List published questions (with answers) for a product template."""
        try:
            tmpl_id = int(product_tmpl_id)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'Invalid product.'}
        limit = min(int(limit or 20), 50)
        offset = max(int(offset or 0), 0)
        Question = request.env['product.question'].sudo()
        domain = [
            ('product_tmpl_id', '=', tmpl_id),
            ('website_published', '=', True),
        ]
        total = Question.search_count(domain)
        questions = Question.search(domain, order='upvote_count desc, create_date desc', limit=limit, offset=offset)
        partner = request.env.user.partner_id if not request.env.user._is_public() else None
        return {
            'ok': True,
            'total': total,
            'questions': [q.to_public_dict(partner=partner) for q in questions],
        }

    # ------------------------------------------------------------------
    # Phase 4 — Search & Aspect Ratings
    # ------------------------------------------------------------------

    @http.route(
        ['/website_sale/review/search'],
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def search_reviews(self, product_tmpl_id, query='', product_id=None,
                        variant_only=False, min_stars=0, with_images_only=False,
                        limit=20, offset=0):
        """Search + quick-filter reviews for the product page search bar.

        Shares the exact moderation/variant domain used everywhere else
        in this module (product.template._rating_domain_for_variant via
        search_reviews()), so a search can never surface an unmoderated
        or wrong-variant review.

        Response: {ok, total, rating_ids, message_ids}
        """
        try:
            tmpl_id = int(product_tmpl_id)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'Invalid product.'}
        Product = request.env['product.template'].sudo().browse(tmpl_id)
        if not Product.exists():
            return {'ok': False, 'error': 'Product not found.'}

        pid = None
        if product_id:
            try:
                pid = int(product_id)
            except (TypeError, ValueError):
                pid = None
        try:
            min_stars = float(min_stars or 0)
        except (TypeError, ValueError):
            min_stars = 0
        limit = min(int(limit or 20), 50)
        offset = max(int(offset or 0), 0)

        result = Product.search_reviews(
            query=query or '',
            product_id=pid,
            variant_only=bool(variant_only) and bool(pid),
            min_stars=min_stars,
            with_images_only=bool(with_images_only),
            limit=limit,
            offset=offset,
        )
        return {
            'ok': True,
            'total': result['total'],
            'rating_ids': result['rating_ids'],
            'message_ids': result['message_ids'],
        }

    @http.route(
        ['/website_sale/review/aspects'],
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def get_review_aspects(self, product_tmpl_id, product_id=None):
        """Configured aspects (for the composer) + their current
        averages (for display on the product page), for one template.

        Response: {ok, aspects: [{id, name}], averages: [{id, name, avg, count}]}
        """
        try:
            tmpl_id = int(product_tmpl_id)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'Invalid product.'}
        Product = request.env['product.template'].sudo().browse(tmpl_id)
        if not Product.exists():
            return {'ok': False, 'error': 'Product not found.'}

        pid = None
        if product_id:
            try:
                pid = int(product_id)
            except (TypeError, ValueError):
                pid = None

        return {
            'ok': True,
            'aspects': Product.get_review_aspects_data(),
            'averages': Product.get_review_aspect_averages(pid),
        }
