import json

from odoo.tests import HttpCase, tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestFeedbackApi(HttpCase, FeedbackTestCommon):
    """End-to-end tests for /api/feedback/* routes, covering both the
    happy path and the error cases required by the SRS (invalid payload,
    unauthorized access, expired token, duplicate submission)."""

    def _post_json(self, url, payload):
        return self.url_open(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )

    def test_01_validate_token_not_found(self):
        response = self.url_open('/api/feedback/token/does-not-exist')
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body['status'], 'invalid')

    def test_02_validate_token_valid(self):
        request = self._create_request()
        response = self.url_open('/api/feedback/token/%s' % request.token)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'valid')
        self.assertFalse(body['already_submitted'])
        self.assertEqual(body['product'], self.product.display_name)
        self.assertNotIn('customer', body)

    def test_03_submit_review_invalid_payload(self):
        request = self._create_request()
        response = self._post_json('/api/feedback/review', {
            'token': request.token,
            'rating': 'not-a-number',
        })
        self.assertEqual(response.status_code, 400)

    def test_04_submit_review_success_then_duplicate_blocked(self):
        request = self._create_request()
        first = self._post_json('/api/feedback/review', {
            'token': request.token,
            'rating': 5,
            'title': 'Great',
            'review': 'Solid, reliable product that does exactly what it promises.',
        })
        self.assertEqual(first.status_code, 201)

        second = self._post_json('/api/feedback/review', {
            'token': request.token,
            'rating': 4,
            'title': 'Again',
            'review': 'Trying to submit a second review for the same token.',
        })
        self.assertEqual(second.status_code, 409)

    def test_05_submit_review_bad_token(self):
        response = self._post_json('/api/feedback/review', {
            'token': 'invalid-token-xyz',
            'rating': 5,
        })
        self.assertEqual(response.status_code, 404)

    def test_06_create_feedback_request_requires_auth(self):
        """auth='user' route: an unauthenticated POST must be rejected."""
        response = self._post_json('/api/feedback/request', {
            'sale_order': self.sale_order.name,
            'customer': self.customer.id,
            'product': self.product.id,
        })
        self.assertIn(response.status_code, (303, 401, 403))

    def test_07_product_reviews_endpoint_structure(self):
        request = self._create_request()
        self._post_json('/api/feedback/review', {
            'token': request.token,
            'rating': 5,
            'title': 'Nice',
            'review': 'Works exactly as described, very happy with the purchase.',
        })
        response = self.url_open('/api/products/%s/reviews' % self.product.product_tmpl_id.id)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('average_rating', body)
        self.assertIn('reviews', body)

    def test_08_product_reviews_exposes_pagination_metadata(self):
        request = self._create_request()
        self._post_json('/api/feedback/review', {
            'token': request.token,
            'rating': 5,
            'title': 'Pagination',
            'review': 'This review is used to verify bounded API pagination metadata.',
        })
        response = self.url_open('/api/products/%s/reviews?limit=1&offset=0' % self.product.product_tmpl_id.id)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['limit'], 1)
        self.assertEqual(body['offset'], 0)
        self.assertIn('has_more', body)
        self.assertIn('next_offset', body)

    def test_09_cancelled_token_rejected(self):
        request = self._create_request()
        request.status = 'cancelled'
        response = self.url_open('/api/feedback/token/%s' % request.token)
        self.assertEqual(response.status_code, 410)

    def test_10_validate_token_expired_rejected(self):
        """Live token-validate endpoint (not just the nightly cron) must
        reject a token whose expiry_date has already passed, and flip the
        request to 'expired' as a side effect (SRS Step 5 test matrix)."""
        from datetime import timedelta

        from odoo import fields as odoo_fields

        request = self._create_request()
        request.write({'expiry_date': odoo_fields.Datetime.now() - timedelta(days=1)})
        response = self.url_open('/api/feedback/token/%s' % request.token)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'expired')
        self.assertEqual(request.status, 'expired')

    def _create_sales_user(self, login='test_sales_api@example.com'):
        user = self.env['res.users'].create({
            'name': 'Test Sales API',
            'login': login,
            'email': login,
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_salesman').id])],
        })
        user.password = 'test12345'
        return user

    def test_11_create_feedback_request_wrong_customer_rejected(self):
        """SRS Step 5 test matrix: a customer who does not belong to the
        sale order must be rejected (403), even for an authorized sales
        user, so a request can't be created against the wrong partner."""
        self._create_sales_user()
        self.authenticate('test_sales_api@example.com', 'test12345')
        other_customer = self.env['res.partner'].create({'name': 'Someone Else'})
        response = self._post_json('/api/feedback/request', {
            'sale_order': self.sale_order.name,
            'customer': other_customer.id,
            'product': self.product.id,
        })
        self.assertEqual(response.status_code, 403)

    def test_12_create_feedback_request_wrong_product_rejected(self):
        """SRS Step 5 test matrix: a product that isn't on the sale order
        must be rejected (400)."""
        self._create_sales_user('test_sales_api2@example.com')
        self.authenticate('test_sales_api2@example.com', 'test12345')
        other_product = self.env['product.product'].create({
            'name': 'Unrelated Product',
            'type': 'consu',
        })
        response = self._post_json('/api/feedback/request', {
            'sale_order': self.sale_order.name,
            'customer': self.customer.id,
            'product': other_product.id,
        })
        self.assertEqual(response.status_code, 400)
