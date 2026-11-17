# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import HttpCase, tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestFeedbackRateLimit(HttpCase, FeedbackTestCommon):
    """Phase 7: public route rate limiting returns HTTP 429 when exceeded."""

    def test_01_token_validate_rate_limit(self):
        feedback_request = self._create_request()
        token = feedback_request.token
        # Force a very low limit for this process window.
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.rate_limit_token_per_min', '5')

        url = '/api/feedback/token/%s' % token
        # Clear any prior cache entries for a deterministic test.
        if hasattr(self.env.registry, '_customer_feedback_rate_limit_cache'):
            self.env.registry._customer_feedback_rate_limit_cache.clear()

        with patch('odoo.addons.customer_feedback.controllers.rate_limit._client_ip',
                   return_value='203.0.113.10'):
            # Import after patch target exists
            from odoo.addons.customer_feedback.controllers import rate_limit
            rate_limit._DEFAULTS['token'] = 5

            ok_codes = []
            limited = False
            for _ in range(8):
                response = self.url_open(url)
                ok_codes.append(response.status_code)
                if response.status_code == 429:
                    limited = True
                    break
            self.assertTrue(
                limited or ok_codes.count(200) <= 5,
                'Expected rate limiting on repeated token validate calls; got %s' % ok_codes,
            )

    def _hammer(self, route_key, url, method='get', payload=None):
        """Force a low limit for route_key, clear the process-local cache,
        then fire repeated requests until the configured limit is exceeded
        or the attempt budget runs out. Returns True if a 429 was observed."""
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.rate_limit_%s_per_min' % route_key, '5')

        if hasattr(self.env.registry, '_customer_feedback_rate_limit_cache'):
            self.env.registry._customer_feedback_rate_limit_cache.clear()

        with patch('odoo.addons.customer_feedback.controllers.rate_limit._client_ip',
                   return_value='203.0.113.20'):
            from odoo.addons.customer_feedback.controllers import rate_limit
            rate_limit._DEFAULTS[route_key] = 5

            for _ in range(8):
                if method == 'get':
                    response = self.url_open(url)
                else:
                    response = self.url_open(
                        url, data=(payload or b''),
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
                if response.status_code == 429:
                    return True
        return False

    def test_02_submit_rate_limit(self):
        """SRS Step 5 test matrix: 'Too many requests -> rate limited' for
        the public review-submit route. The rate-limit check runs before
        token lookup, so a bogus/reused token is enough to trigger it."""
        limited = self._hammer(
            'submit', '/feedback/review/does-not-exist/submit', method='post',
            payload=b'rating=5')
        self.assertTrue(limited, 'Expected 429 on repeated submit calls to the same token bucket.')

    def test_03_vote_rate_limit(self):
        """SRS Step 5 test matrix: rate limiting on the helpful/not-helpful
        vote route."""
        limited = self._hammer(
            'vote', '/feedback/review/999999/vote', method='post',
            payload=b'vote_type=helpful')
        self.assertTrue(limited, 'Expected 429 on repeated vote calls to the same review bucket.')

    def test_04_public_get_rate_limit(self):
        """SRS Step 5 test matrix: rate limiting on the public product-reviews
        listing route."""
        limited = self._hammer(
            'public_get', '/feedback/product/%s/reviews' % self.product.product_tmpl_id.id)
        self.assertTrue(limited, 'Expected 429 on repeated public product-reviews calls.')
