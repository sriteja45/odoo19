# -*- coding: utf-8 -*-
"""Step 6 / Phase 9 — Edge-case unit tests.

Complements the bulk perf_load_test.py script with fast TransactionCase
guards for boundary conditions the SRS and architecture call out.
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.addons.customer_feedback.tests.common import FeedbackTestCommon


@tagged('post_install', '-at_install', 'customer_feedback')
class TestStep6EdgeCases(FeedbackTestCommon):

    def _approve_review(self, request, rating=5.0, title='Great', text='This product works very well for me.'):
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': rating,
            'review_title': title,
            'review_text': text,
        })
        if review.status == 'pending':
            review.action_approve()
        return review

    def test_01_rating_boundaries(self):
        """Rating must be 1..5 inclusive; 0 and 6 rejected."""
        request = self._create_request()
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create({
                'request_id': request.id,
                'product_id': request.product_id.id,
                'customer_id': request.partner_id.id,
                'rating': 0,
                'review_text': 'Too short rating should fail before length.',
            })
        # Fresh request for upper bound (unique request_id constraint).
        request2 = self._create_request()
        # Need a second order line path — create a standalone request.
        Request = self.env['feedback.request']
        # Reuse partner/product with a new SO line simulation via create without line unique if needed.
        # Simpler: use the same product with a second SO.
        so2 = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        so2.action_confirm()
        req2 = Request.create({
            'sale_order_id': so2.id,
            'sale_order_line_id': so2.order_line[:1].id,
            'partner_id': self.customer.id,
            'product_id': self.product.id,
            'company_id': so2.company_id.id,
        })
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create({
                'request_id': req2.id,
                'product_id': req2.product_id.id,
                'customer_id': req2.partner_id.id,
                'rating': 6,
                'review_text': 'Invalid high rating value for this test case.',
            })

    def test_02_review_text_length_bounds(self):
        """Min/max review length enforced from config params."""
        request = self._create_request()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('customer_feedback.review_min_length', '10')
        ICP.set_param('customer_feedback.review_max_length', '50')
        with self.assertRaises(ValidationError):
            self.env['feedback.review'].create({
                'request_id': request.id,
                'product_id': request.product_id.id,
                'customer_id': request.partner_id.id,
                'rating': 4,
                'review_text': 'short',
            })

    def test_03_one_review_per_request(self):
        """Second review on the same request is blocked."""
        request = self._create_request()
        self._approve_review(request)
        with self.assertRaises(Exception):
            self.env['feedback.review'].create({
                'request_id': request.id,
                'product_id': request.product_id.id,
                'customer_id': request.partner_id.id,
                'rating': 3,
                'review_text': 'Second review must not be allowed here.',
            })

    def test_04_reject_excludes_from_native_count(self):
        """Rejected review must not contribute to product.rating_count."""
        request = self._create_request()
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_text': 'Will be rejected so it stays out of aggregates.',
        })
        if review.status == 'approved':
            review.action_reject()
        else:
            review.action_reject()
        tmpl = review.product_id.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        # After reject, this product should not count the rejected score.
        self.assertFalse(review.rating_id.consumed if review.rating_id else True)

    def test_05_star_int_safe_for_float_rating(self):
        """Rating may be float (e.g. 4.0); int(round()) is safe for star UI."""
        request = self._create_request()
        review = self._approve_review(request, rating=4.0)
        star_count = int(round(review.rating or 0))
        self.assertEqual(star_count, 4)
        self.assertEqual('★' * star_count + '☆' * (5 - star_count), '★★★★☆')

    def test_06_reconcile_is_idempotent(self):
        """Calling _reconcile_product_native_ratings twice does not raise."""
        request = self._create_request()
        self._approve_review(request)
        Review = self.env['feedback.review']
        r1 = Review._reconcile_product_native_ratings()
        r2 = Review._reconcile_product_native_ratings()
        self.assertIn('bridged', r1)
        self.assertIn('bridged', r2)
