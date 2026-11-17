import json
import logging
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields, http
from odoo.http import request

from .rate_limit import check_rate_limit

_logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Raised by helper methods to short-circuit a route with a JSON error response."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class FeedbackApiController(http.Controller):
    """REST API for the Customer Feedback module (SRS Section 15).

    Implemented with type='http' rather than type='json' (JSON-RPC) so that
    routes can return real HTTP status codes (201/400/404/409/...) and a flat
    JSON body, as specified by the SRS, instead of being wrapped in a
    JSON-RPC 2.0 envelope that always answers with HTTP 200.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    def _success(self, payload, status=200):
        body = {'status': 'success'}
        body.update(payload)
        return self._json_response(body, status=status)

    def _error(self, code, message):
        return self._json_response({'status': 'error', 'code': code, 'message': message}, status=code)

    def _rate_limited(self, route_key, extra_key=None):
        reason = check_rate_limit(route_key, extra_key=extra_key)
        if reason:
            return self._error(429, reason)
        return None

    def _get_json_body(self):
        try:
            raw = request.httprequest.get_data()
            return json.loads(raw.decode('utf-8')) if raw else {}
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, 'Request body must be valid JSON.')

    def _get_request_by_token(self, token):
        # Tokens are bearer credentials. Keep lookup exact, never log the token,
        # and reject obviously malformed values before hitting the database.
        if not token or len(token) > 128 or any(c.isspace() for c in token):
            return request.env['feedback.request'].browse()
        return request.env['feedback.request'].sudo().search([('token', '=', token)], limit=1)

    def _can_create_request(self):
        user = request.env.user
        return (
            user.has_group('sales_team.group_sale_salesman') or
            user.has_group('customer_feedback.group_feedback_manager')
        )

    # ------------------------------------------------------------------
    # API 1 - Create Feedback Request
    # ------------------------------------------------------------------
    @http.route('/api/feedback/request', type='http', auth='user', methods=['POST'], csrf=False)
    def create_feedback_request(self, **kwargs):
        try:
            data = self._get_json_body()

            if not self._can_create_request():
                return self._error(403, 'You are not authorized to create feedback requests.')

            order_ref = data.get('sale_order')
            customer_id = data.get('customer')
            product_id = data.get('product')

            if not order_ref or not customer_id or not product_id:
                return self._error(400, 'sale_order, customer and product are required.')

            env = request.env
            sale_order = env['sale.order'].sudo().search([
                ('name', '=', order_ref),
                ('company_id', 'in', request.env.user.company_ids.ids),
            ], limit=1)
            if not sale_order:
                return self._error(404, 'Sale Order not found.')

            if sale_order.state == 'cancel':
                return self._error(400, 'Sale Order is cancelled.')

            customer = env['res.partner'].sudo().browse(int(customer_id))
            if not customer.exists():
                return self._error(404, 'Customer not found.')
            if customer.id != sale_order.partner_id.id:
                return self._error(403, 'Customer does not belong to this Sale Order.')

            product = env['product.product'].sudo().browse(int(product_id))
            if not product.exists() or not product.active:
                return self._error(404, 'Product not found.')

            order_line = sale_order.order_line.filtered(lambda line: line.product_id.id == product.id)
            if not order_line:
                return self._error(400, 'Product does not belong to this Sale Order.')
            order_line = order_line[0]

            if order_line.product_uom_qty and order_line.qty_delivered + 1e-6 < order_line.product_uom_qty:
                return self._error(400, 'Product not fully delivered yet.')

            done_pickings = sale_order.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing'
                and product.id in p.move_ids.mapped('product_id').ids
            )
            if not done_pickings:
                return self._error(400, 'Product not delivered yet.')
            picking = done_pickings.sorted('date_done', reverse=True)[0]

            existing = env['feedback.request'].sudo().search(
                [('sale_order_line_id', '=', order_line.id)], limit=1)
            if existing:
                return self._error(409, 'A feedback request already exists for this order line.')

            Request = env['feedback.request'].sudo()
            expiry_days = Request._get_expiry_days()
            delivery_date = picking.date_done or fields.Datetime.now()
            try:
                with env.cr.savepoint():
                    feedback_request = Request.create({
                        'sale_order_id': sale_order.id,
                        'sale_order_line_id': order_line.id,
                        'picking_id': picking.id,
                        'partner_id': customer.id,
                        'product_id': product.id,
                        'company_id': sale_order.company_id.id,
                        'delivery_date': delivery_date,
                        'expiry_date': delivery_date + timedelta(days=expiry_days),
                    })
            except IntegrityError:
                return self._error(409, 'A feedback request already exists for this order line.')

            return self._success({
                'token': feedback_request.token,
                'expiry': feedback_request.expiry_date.date().isoformat(),
            }, status=201)

        except ApiError as exc:
            return self._error(exc.code, exc.message)
        except ValueError:
            return self._error(400, 'customer and product must be numeric IDs.')
        except Exception:
            _logger.exception('Customer Feedback API: unexpected error in create_feedback_request')
            return self._error(500, 'Internal server error.')

    # ------------------------------------------------------------------
    # API 2 - Validate Token
    # ------------------------------------------------------------------
    @http.route('/api/feedback/token/<string:token>', type='http', auth='public', methods=['GET'], csrf=False)
    def validate_token(self, token, **kwargs):
        try:
            limited = self._rate_limited('token', extra_key=(token or '')[:16])
            if limited:
                return limited

            feedback_request = self._get_request_by_token(token)
            if not feedback_request:
                return self._json_response(
                    {'status': 'invalid', 'code': 404, 'message': 'Token not found.'}, status=404)

            if feedback_request.status == 'cancelled':
                return self._json_response({'status': 'cancelled', 'message': 'This feedback request is no longer active.'}, status=410)

            if feedback_request.status == 'submitted':
                return self._json_response({
                    'status': 'already_submitted',
                    'already_submitted': True,
                    'message': 'A review has already been submitted for this token.',
                })

            if feedback_request.expiry_date and feedback_request.expiry_date < fields.Datetime.now():
                if feedback_request.status != 'expired':
                    feedback_request.status = 'expired'
                return self._json_response({
                    'status': 'expired',
                    'message': 'This feedback link has expired.',
                })

            return self._json_response({
                'status': 'valid',
                'already_submitted': False,
                'product': feedback_request.product_id.display_name,
                'expiry': feedback_request.expiry_date.date().isoformat() if feedback_request.expiry_date else None,
            })

        except Exception:
            _logger.exception('Customer Feedback API: unexpected error in validate_token')
            return self._error(500, 'Internal server error.')

    # ------------------------------------------------------------------
    # API 3 - Submit Review
    # ------------------------------------------------------------------
    @http.route('/api/feedback/review', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_review(self, **kwargs):
        try:
            data = self._get_json_body()
            token = data.get('token')
            limited = self._rate_limited('submit', extra_key=(token or '')[:16])
            if limited:
                return limited

            if not token:
                return self._error(400, 'token is required.')

            feedback_request = self._get_request_by_token(token)
            if not feedback_request:
                return self._error(404, 'Token not found.')

            if feedback_request.status == 'cancelled':
                return self._error(410, 'This feedback request is no longer active.')

            if feedback_request.status == 'submitted':
                return self._error(409, 'A review has already been submitted for this token.')

            if feedback_request.expiry_date and feedback_request.expiry_date < fields.Datetime.now():
                feedback_request.status = 'expired'
                return self._error(400, 'This feedback link has expired.')

            if feedback_request.status not in ('pending', 'sent'):
                return self._error(400, 'This token is not open for review submission.')

            try:
                rating = int(data.get('rating'))
            except (TypeError, ValueError):
                return self._error(400, 'rating must be an integer between 1 and 5.')

            if rating < 1 or rating > 5:
                return self._error(400, 'Rating must be between 1 and 5.')

            review_title = (data.get('title') or '').strip()
            review_text = (data.get('review') or '').strip()

            env = request.env
            min_len = int(env['ir.config_parameter'].sudo().get_param(
                'customer_feedback.review_min_length', default=10))
            max_len = int(env['ir.config_parameter'].sudo().get_param(
                'customer_feedback.review_max_length', default=2000))
            if review_text and len(review_text) < min_len:
                return self._error(400, 'Review text must be at least %d characters.' % min_len)
            if review_text and len(review_text) > max_len:
                return self._error(400, 'Review text must not exceed %d characters.' % max_len)

            try:
                with env.cr.savepoint():
                    env['feedback.review'].sudo().create({
                        'request_id': feedback_request.id,
                        'product_id': feedback_request.product_id.id,
                        'customer_id': feedback_request.partner_id.id,
                        'rating': rating,
                        'review_title': review_title,
                        'review_text': review_text,
                        'review_date': fields.Datetime.now(),
                        'is_verified': True,
                    })
            except IntegrityError:
                return self._error(409, 'A review has already been submitted for this token.')

            return self._success({'message': 'Review submitted successfully'}, status=201)

        except ApiError as exc:
            return self._error(exc.code, exc.message)
        except Exception:
            _logger.exception('Customer Feedback API: unexpected error in submit_review')
            return self._error(500, 'Internal server error.')

    # ------------------------------------------------------------------
    # API 4 - Product Reviews
    # ------------------------------------------------------------------
    @http.route('/api/products/<int:product_id>/reviews', type='http', auth='public', methods=['GET'], csrf=False)
    def product_reviews(self, product_id, limit=20, offset=0, **kwargs):
        try:
            limited = self._rate_limited('public_get', extra_key=str(product_id))
            if limited:
                return limited

            template = request.env['product.template'].sudo().browse(product_id)
            if not template.exists():
                return self._error(404, 'Product not found.')

            # Do not expose review payloads for products that are not published
            # on the website (reduces product enumeration via this public API).
            if hasattr(template, 'is_published') and not template.is_published:
                return self._error(404, 'Product not found.')

            try:
                limit = max(1, min(int(limit), 100))
                offset = max(0, int(offset))
            except ValueError:
                limit, offset = 20, 0

            page = template.get_public_review_page(
                sort='newest', limit=limit, offset=offset)
            reviews = page['reviews']

            return self._json_response({
                'product': template.name,
                'average_rating': template.rating_avg,
                'review_count': template.rating_count,
                'distribution': {
                    str(k): v for k, v in template.get_rating_distribution().items()
                },
                'limit': page['limit'],
                'offset': page['offset'],
                'has_more': page['has_more'],
                'next_offset': page['next_offset'],
                'reviews': [{
                    'customer': review.get_display_name_public(),
                    'rating': review.rating,
                    'title': review.review_title,
                    'review': review.review_text,
                    'date': review.review_date.date().isoformat() if review.review_date else None,
                    'verified': review.is_verified,
                } for review in reviews],
            })

        except Exception:
            _logger.exception('Customer Feedback API: unexpected error in product_reviews')
            return self._error(500, 'Internal server error.')

    # ------------------------------------------------------------------
    # API 5 - Customer Reviews
    # ------------------------------------------------------------------
    @http.route('/api/customer/reviews', type='http', auth='user', methods=['GET'], csrf=False)
    def customer_reviews(self, limit=20, offset=0, **kwargs):
        try:
            try:
                limit = max(1, min(int(limit), 100))
                offset = max(0, int(offset))
            except (TypeError, ValueError):
                return self._error(400, 'limit and offset must be valid integers.')

            partner = request.env.user.partner_id
            rows = request.env['feedback.review'].sudo().search(
                [('customer_id', '=', partner.id)],
                order='review_date desc, id desc', limit=limit + 1, offset=offset)
            has_more = len(rows) > limit
            reviews = rows[:limit]
            status_labels = dict(reviews._fields['status'].selection)

            return self._json_response({
                'customer': partner.name,
                'limit': limit,
                'offset': offset,
                'has_more': has_more,
                'next_offset': offset + limit if has_more else None,
                'reviews': [{
                    'product': review.product_id.display_name,
                    'rating': review.rating,
                    'status': status_labels.get(review.status, review.status),
                    'date': review.review_date.date().isoformat() if review.review_date else None,
                } for review in reviews],
            })

        except Exception:
            _logger.exception('Customer Feedback API: unexpected error in customer_reviews')
            return self._error(500, 'Internal server error.')
