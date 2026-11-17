import json

from psycopg2 import IntegrityError

from odoo import fields, http
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .rate_limit import check_rate_limit


class FeedbackPortalController(http.Controller):

    def _get_request(self, token):
        return request.env['feedback.request'].sudo().search([('token', '=', token)], limit=1)

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _is_edit_allowed(self):
        return request.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.allow_review_edit', default='False') == 'True'

    def _rate_limited_json(self, route_key, extra_key=None):
        reason = check_rate_limit(route_key, extra_key=extra_key)
        if reason:
            return self._json_response({'error': reason}, status=429)
        return None

    @http.route(['/feedback/review/<string:token>'], type='http', auth='public', website=True, sitemap=False)
    def feedback_review_form(self, token, **kwargs):
        feedback_request = self._get_request(token)
        if not feedback_request:
            return request.render('customer_feedback.portal_invalid_token')

        if feedback_request.status == 'cancelled':
            return request.render('customer_feedback.portal_invalid_token')

        if feedback_request.status == 'submitted':
            return request.render('customer_feedback.portal_already_submitted', {
                'review': feedback_request.review_id,
                'token': token,
                'allow_edit': self._is_edit_allowed(),
            })

        if feedback_request.status == 'expired' or (
                feedback_request.expiry_date and feedback_request.expiry_date < fields.Datetime.now()):
            feedback_request.status = 'expired'
            return request.render('customer_feedback.portal_expired_token')

        return request.render('customer_feedback.portal_review_form', {
            'feedback_request': feedback_request,
            'error': kwargs.get('error'),
        })

    @http.route(['/feedback/review/<string:token>/submit'], type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def feedback_review_submit(self, token, **post):
        # CSRF already protects this form POST; rate-limit still blocks scripted floods.
        if check_rate_limit('submit', extra_key=(token or '')[:16]):
            return request.redirect('/feedback/review/%s?error=rate' % token)

        feedback_request = self._get_request(token)
        if not feedback_request or feedback_request.status not in ('pending', 'sent'):
            return request.redirect('/feedback/review/%s' % token)

        if feedback_request.expiry_date and feedback_request.expiry_date < fields.Datetime.now():
            feedback_request.status = 'expired'
            return request.redirect('/feedback/review/%s' % token)

        try:
            rating = int(post.get('rating', 0))
        except (TypeError, ValueError):
            rating = 0

        if rating < 1 or rating > 5:
            return request.redirect('/feedback/review/%s?error=rating' % token)

        review_text = (post.get('review_text') or '').strip()
        review_title = (post.get('review_title') or '').strip()

        min_len = int(request.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.review_min_length', default=10))
        if review_text and len(review_text) < min_len:
            return request.redirect('/feedback/review/%s?error=length' % token)

        try:
            with request.env.cr.savepoint():
                review = request.env['feedback.review'].sudo().create({
                    'request_id': feedback_request.id,
                    'product_id': feedback_request.product_id.id,
                    'customer_id': feedback_request.partner_id.id,
                    'rating': rating,
                    'review_title': review_title,
                    'review_text': review_text,
                    'review_date': fields.Datetime.now(),
                    'is_verified': True,
                })
                # Step 8 — attach uploaded photos/videos (ir.attachment storage)
                files = request.httprequest.files.getlist('media_files')
                if files:
                    request.env['feedback.review.media'].sudo().create_from_uploads(
                        review, files,
                    )
        except IntegrityError:
            return request.redirect('/feedback/review/%s' % token)
        except Exception:
            return request.redirect('/feedback/review/%s?error=media' % token)

        return request.redirect('/feedback/review/%s' % token)

    @http.route(['/feedback/review/<string:token>/edit'], type='http', auth='public', website=True, sitemap=False)
    def feedback_review_edit_form(self, token, **kwargs):
        feedback_request = self._get_request(token)
        if not feedback_request:
            return request.render('customer_feedback.portal_invalid_token')

        if feedback_request.status == 'cancelled':
            return request.render('customer_feedback.portal_invalid_token')

        if feedback_request.expiry_date and feedback_request.expiry_date < fields.Datetime.now():
            feedback_request.status = 'expired'
            return request.render('customer_feedback.portal_expired_token')

        if feedback_request.status != 'submitted' or not feedback_request.review_id:
            # Nothing to edit yet - send them to the normal review form.
            return request.redirect('/feedback/review/%s' % token)

        if not self._is_edit_allowed():
            return request.render('customer_feedback.portal_edit_disabled', {
                'token': token,
            })

        return request.render('customer_feedback.portal_review_edit_form', {
            'feedback_request': feedback_request,
            'review': feedback_request.review_id,
            'error': kwargs.get('error'),
        })

    @http.route(['/feedback/review/<string:token>/edit'], type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def feedback_review_edit_submit(self, token, **post):
        feedback_request = self._get_request(token)
        if not feedback_request or feedback_request.status != 'submitted' or not feedback_request.review_id:
            return request.redirect('/feedback/review/%s' % token)

        if feedback_request.status == 'cancelled':
            return request.render('customer_feedback.portal_invalid_token')

        if feedback_request.expiry_date and feedback_request.expiry_date < fields.Datetime.now():
            feedback_request.status = 'expired'
            return request.redirect('/feedback/review/%s' % token)

        if not self._is_edit_allowed():
            return request.redirect('/feedback/review/%s' % token)

        try:
            rating = int(post.get('rating', 0))
        except (TypeError, ValueError):
            rating = 0

        if rating < 1 or rating > 5:
            return request.redirect('/feedback/review/%s/edit?error=rating' % token)

        review_text = (post.get('review_text') or '').strip()
        review_title = (post.get('review_title') or '').strip()

        min_len = int(request.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.review_min_length', default=10))
        if review_text and len(review_text) < min_len:
            return request.redirect('/feedback/review/%s/edit?error=length' % token)

        feedback_request.review_id.sudo().action_customer_edit({
            'rating': rating,
            'review_title': review_title,
            'review_text': review_text,
        })

        return request.redirect('/feedback/review/%s' % token)

    _SORT_OPTIONS = {
        'newest': 'newest',
        'highest': 'highest',
        'lowest': 'lowest',
    }
    _PUBLIC_REVIEW_LIMIT = 20

    @http.route(['/feedback/product/<int:product_id>/reviews'], type='http', auth='public',
                website=True, methods=['GET'], csrf=False)
    def feedback_product_reviews(self, product_id, sort=None, rating=None, **kwargs):
        """Return just the reviews-list fragment for a product, sorted per
        the 'sort' query param (newest/highest/lowest) and optionally
        restricted to one or more star ratings via 'rating' (comma-separated,
        e.g. 'rating=5,4'). Used by the sort dropdown and star filter buttons
        on the product page to refresh the list via fetch() instead of a
        full page reload."""
        limited = self._rate_limited_json('public_get', extra_key=str(product_id))
        if limited:
            return limited

        template = request.env['product.template'].sudo().browse(product_id)
        if not template.exists() or not template.is_published:
            return self._json_response({'error': 'Product not found.'}, status=404)

        try:
            limit = max(1, min(int(kwargs.get('limit', self._PUBLIC_REVIEW_LIMIT)), 100))
            offset = max(0, int(kwargs.get('offset', 0)))
        except (TypeError, ValueError):
            return self._json_response({'error': 'Invalid pagination values.'}, status=400)

        ratings = None
        if rating:
            try:
                ratings = sorted({int(r) for r in rating.split(',') if r.strip()})
            except ValueError:
                return self._json_response({'error': 'Invalid rating filter.'}, status=400)
            ratings = [r for r in ratings if 1 <= r <= 5]
            if not ratings:
                return request.render('customer_feedback.product_reviews_list', {
                    'product': template,
                    'reviews': request.env['feedback.review'].sudo().browse(),
                    'has_more': False,
                    'next_offset': None,
                })

        page = template.get_public_review_page(
            sort=self._SORT_OPTIONS.get(sort, 'newest'),
            ratings=ratings, limit=limit, offset=offset)

        return request.render('customer_feedback.product_reviews_list', {
            'product': template,
            **page,
        })

    @http.route(['/feedback/review/<int:review_id>/vote'], type='http', auth='public',
                website=True, methods=['POST'], csrf=False)
    def feedback_review_vote(self, review_id, **post):
        """Cast, change, or retract a Helpful / Not Helpful vote on an
        approved review. One vote per visitor: logged-in users are keyed by
        partner, anonymous visitors by their website session id, so voting
        again with the same choice retracts it (toggle) and voting with the
        other choice switches it."""
        limited = self._rate_limited_json('vote', extra_key=str(review_id))
        if limited:
            return limited

        vote_type = post.get('vote_type')
        if vote_type not in ('helpful', 'not_helpful'):
            return self._json_response({'error': 'Invalid vote type.'}, status=400)

        review = request.env['feedback.review'].sudo().browse(review_id)
        if not review.exists() or review.status != 'approved':
            return self._json_response({'error': 'Review not found.'}, status=404)

        user = request.env.user
        partner = user.partner_id if not user._is_public() else False
        voter_key = 'partner-%s' % partner.id if partner else 'session-%s' % request.session.sid

        action = request.env['feedback.review.vote'].sudo().apply_vote(
            review, voter_key, vote_type, partner.id if partner else False)

        return self._json_response({
            'action': action,
            'helpful_count': review.helpful_count,
            'not_helpful_count': review.not_helpful_count,
        })

    @http.route(['/my/reviews'], type='http', auth='user', website=True)
    def my_reviews(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        Review = request.env['feedback.review'].sudo()
        domain = [('customer_id', '=', partner.id)]
        total = Review.search_count(domain)
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        pager = portal_pager(
            url='/my/reviews', total=total, page=page, step=20, url_args={})
        reviews = Review.search(
            domain, order='review_date desc, id desc',
            limit=20, offset=pager['offset'])
        return request.render('customer_feedback.portal_my_reviews', {
            'reviews': reviews,
            'pager': pager,
            'allow_edit': self._is_edit_allowed(),
        })
