from odoo.tests import HttpCase, tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestFeedbackProductReviewsSort(HttpCase, FeedbackTestCommon):
    """End-to-end tests for /feedback/product/<id>/reviews, the fragment
    endpoint the website sort dropdown calls to re-order approved reviews
    without a full page reload."""

    def _make_review(self, rating, days_ago=0):
        from datetime import timedelta
        from odoo import fields

        request = self.env['feedback.request'].create({
            'sale_order_id': self.sale_order.id,
            'sale_order_line_id': self.sale_order.order_line[:1].id,
            'partner_id': self.customer.id,
            'product_id': self.product.id,
            'company_id': self.sale_order.company_id.id,
        })
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': self.product.id,
            'customer_id': self.customer.id,
            'rating': rating,
            'review_text': 'Review with rating %s' % rating,
            'review_date': fields.Datetime.now() - timedelta(days=days_ago),
        })
        review.action_approve()
        return review

    def _order_of_ratings(self, html):
        # Star glyphs appear once per review card in document order, so the
        # sequence of full-star counts tells us the order the reviews render in.
        import re
        return [chunk.count('\u2605') for chunk in re.findall(
            r'text-warning">(.*?)</div>', html, re.S)]

    def setUp(self):
        super().setUp()
        # Remove any request auto-created for the shared order line so each
        # test's manually-created reviews are the only ones present.
        self.env['feedback.request'].search([('sale_order_id', '=', self.sale_order.id)]).unlink()
        self.env['feedback.review'].search([('product_id', '=', self.product.id)]).unlink()

        self.env['ir.config_parameter'].sudo().set_param('customer_feedback.moderation_enabled', 'False')
        self._make_review(rating=3, days_ago=5)
        self._make_review(rating=5, days_ago=2)
        self._make_review(rating=1, days_ago=0)

    def test_default_sort_is_newest_first(self):
        response = self.url_open(
            '/feedback/product/%s/reviews' % self.product.product_tmpl_id.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._order_of_ratings(response.text), [1, 5, 3])

    def test_sort_highest_rated_first(self):
        response = self.url_open(
            '/feedback/product/%s/reviews?sort=highest' % self.product.product_tmpl_id.id)
        self.assertEqual(self._order_of_ratings(response.text), [5, 3, 1])

    def test_sort_lowest_rated_first(self):
        response = self.url_open(
            '/feedback/product/%s/reviews?sort=lowest' % self.product.product_tmpl_id.id)
        self.assertEqual(self._order_of_ratings(response.text), [1, 3, 5])

    def test_unknown_product_returns_404(self):
        response = self.url_open('/feedback/product/999999/reviews')
        self.assertEqual(response.status_code, 404)

    def test_filter_single_rating(self):
        response = self.url_open(
            '/feedback/product/%s/reviews?rating=5' % self.product.product_tmpl_id.id)
        self.assertEqual(self._order_of_ratings(response.text), [5])

    def test_filter_multiple_ratings(self):
        response = self.url_open(
            '/feedback/product/%s/reviews?rating=5,1' % self.product.product_tmpl_id.id)
        self.assertEqual(sorted(self._order_of_ratings(response.text)), [1, 5])

    def test_filter_combined_with_sort(self):
        response = self.url_open(
            '/feedback/product/%s/reviews?sort=lowest&rating=5,3,1'
            % self.product.product_tmpl_id.id)
        self.assertEqual(self._order_of_ratings(response.text), [1, 3, 5])

    def test_filter_no_matches_shows_empty_state(self):
        self._make_review(rating=2, days_ago=1)
        response = self.url_open(
            '/feedback/product/%s/reviews?rating=4' % self.product.product_tmpl_id.id)
        self.assertIn('No reviews yet', response.text)

    def test_filter_invalid_value_ignored_gracefully(self):
        response = self.url_open(
            '/feedback/product/%s/reviews?rating=not-a-number' % self.product.product_tmpl_id.id)
        self.assertEqual(response.status_code, 400)

    def test_pagination_returns_bounded_first_page_and_load_more(self):
        for index in range(22):
            self._make_review(rating=(index % 5) + 1, days_ago=10 + index)

        first = self.url_open(
            '/feedback/product/%s/reviews?limit=20&offset=0' % self.product.product_tmpl_id.id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.text.count('class="o_feedback_review border-bottom py-3"'), 20)
        self.assertIn('o_feedback_load_more_btn', first.text)
        self.assertIn('data-offset="20"', first.text)

        second = self.url_open(
            '/feedback/product/%s/reviews?limit=20&offset=20' % self.product.product_tmpl_id.id)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.text.count('class="o_feedback_review border-bottom py-3"'), 5)
        self.assertNotIn('o_feedback_load_more_btn', second.text)

    def test_toolbar_renders_sort_and_star_filter_controls(self):
        """Phase 6: the backend sort/filter endpoint above is only useful if
        the product page actually renders controls that call it. Render the
        snippet template directly (cheaper and more targeted than a full
        product page HttpCase visit) and check the sort dropdown + one star
        filter button per rating value are present with the attributes the
        frontend Interaction (feedback_review_vote.js) expects."""
        html = self.env['ir.qweb']._render(
            'customer_feedback.s_feedback_reviews', {'product': self.product.product_tmpl_id})
        self.assertIn('o_feedback_sort_select', html)
        for stars in (5, 4, 3, 2, 1):
            self.assertIn('data-rating="%s"' % stars, html)
        self.assertIn('o_feedback_reviews_list_container', html)
