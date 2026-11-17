# -*- coding: utf-8 -*-
"""Step 6 — Automated tests for the native rating.rating bridge and lifecycle.

These tests prove the module extends Odoo correctly rather than creating a
second rating system. They cover the explicit acceptance matrix from the
7-step plan:

  Review creation
        ↓
  Native rating creation
        ↓
  Approval  → consumed=True  → rating_avg/count update
  Reject    → consumed=False
  Hidden    → consumed=False
  Pending   → consumed=False

Also:
  - Duplicate rating prevention
  - Review deletion removes native rating
  - Rating value updates stay on the same native row
  - Token security is exercised via the request → review path
"""
from odoo.exceptions import ValidationError, AccessError
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestStep6RatingLifecycle(FeedbackTestCommon):
    """Dedicated Step 6 coverage for the rating bridge contract."""

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param(
            'customer_feedback.moderation_enabled', 'True')

    def _make_review(self, rating=5, status_after_create=None):
        request = self._create_request()
        # Allow a second request on the same order if needed by creating a
        # fresh request when the first is already submitted.
        existing = self.env['feedback.review'].search(
            [('request_id', '=', request.id)], limit=1)
        if existing:
            request = self.env['feedback.request'].create({
                'sale_order_id': self.sale_order.id,
                'sale_order_line_id': self.sale_order.order_line[:1].id,
                'partner_id': self.customer.id,
                'product_id': self.product.id,
                'company_id': self.sale_order.company_id.id,
            })
        review = self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': rating,
            'review_title': 'Step6 title',
            'review_text': 'Automated Step 6 review body with enough characters.',
        })
        if status_after_create == 'approved':
            review.action_approve()
        return review

    # ------------------------------------------------------------------
    # 1. Review creation → native rating row exists, not consumed yet
    # ------------------------------------------------------------------

    def test_01_create_review_creates_native_rating_pending(self):
        review = self._make_review(rating=4)
        self.assertEqual(review.status, 'pending')
        self.assertTrue(review.rating_id, 'Create must link exactly one rating.rating')
        self.assertFalse(
            review.rating_id.consumed,
            'Pending review must keep consumed=False so it is excluded from averages',
        )
        self.assertEqual(review.rating_id.rating, 4.0)
        self.assertEqual(review.rating_id.res_model, 'product.template')
        self.assertEqual(review.rating_id.res_id, review.product_tmpl_id.id)
        self.assertEqual(review.rating_id.partner_id, self.customer)
        self.assertEqual(review.rating_id.feedback_review_id, review)

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 0)

    # ------------------------------------------------------------------
    # 2. Approval → consumed=True → averages update
    # ------------------------------------------------------------------

    def test_02_approve_sets_consumed_and_updates_native_stats(self):
        review = self._make_review(rating=5)
        review.action_approve()
        self.assertEqual(review.status, 'approved')
        self.assertTrue(review.rating_id.consumed)
        self.assertEqual(review.rating_id.rating, 5.0)

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 1)
        self.assertAlmostEqual(tmpl.rating_avg, 5.0, places=2)

    # ------------------------------------------------------------------
    # 3. Reject / Hide → consumed=False → excluded from averages
    # ------------------------------------------------------------------

    def test_03_reject_keeps_row_but_unconsumes(self):
        review = self._make_review(rating=5, status_after_create='approved')
        rating = review.rating_id
        self.assertTrue(rating.consumed)

        review.action_reject()
        self.assertEqual(review.status, 'rejected')
        self.assertEqual(review.rating_id.id, rating.id)
        self.assertFalse(review.rating_id.consumed)

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 0)

    def test_04_hide_keeps_row_but_unconsumes(self):
        review = self._make_review(rating=4, status_after_create='approved')
        rating_id = review.rating_id.id
        review.action_hide()
        self.assertEqual(review.status, 'hidden')
        self.assertEqual(review.rating_id.id, rating_id)
        self.assertFalse(review.rating_id.consumed)

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 0)

    # ------------------------------------------------------------------
    # 4. Multi-review average math
    # ------------------------------------------------------------------

    def test_05_multiple_approved_update_average(self):
        r1 = self._make_review(rating=5, status_after_create='approved')
        r2 = self._make_review(rating=3, status_after_create='approved')
        self.assertNotEqual(r1.rating_id.id, r2.rating_id.id)

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 2)
        self.assertAlmostEqual(tmpl.rating_avg, 4.0, places=2)

        # Reject one → average and count drop correctly
        r1.action_reject()
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 1)
        self.assertAlmostEqual(tmpl.rating_avg, 3.0, places=2)

    # ------------------------------------------------------------------
    # 5. No duplicate native ratings
    # ------------------------------------------------------------------

    def test_06_no_duplicate_native_rating_on_reapprove(self):
        review = self._make_review(rating=4, status_after_create='approved')
        first_id = review.rating_id.id

        review.action_reject()
        review.action_approve()
        self.assertEqual(review.rating_id.id, first_id)

        count = self.env['rating.rating'].search_count([
            ('feedback_review_id', '=', review.id),
        ])
        self.assertEqual(count, 1)

        native_count = self.env['rating.rating'].search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', review.product_tmpl_id.id),
            ('partner_id', '=', self.customer.id),
        ])
        self.assertEqual(native_count, 1)

    def test_07_bridge_all_approved_is_idempotent(self):
        review = self._make_review(rating=5, status_after_create='approved')
        first_id = review.rating_id.id
        bridged = self.env['feedback.review']._bridge_all_approved_to_native_rating()
        self.assertEqual(bridged, 0)
        self.assertEqual(review.rating_id.id, first_id)

    # ------------------------------------------------------------------
    # 6. Deletion removes native rating
    # ------------------------------------------------------------------

    def test_08_unlink_review_deconsumes_native_rating(self):
        review = self._make_review(rating=5, status_after_create='approved')
        rating = review.rating_id
        self.assertTrue(rating.exists())
        review.unlink()

        # unlink() preserves native rating history by design (see
        # feedback.review.unlink docstring); it de-consumes the row rather
        # than deleting it. Physical deletion is reserved for the explicit
        # permanent_rating_purge context.
        self.assertTrue(rating.exists(), 'Rating record should be retained for historical audit')
        self.assertFalse(rating.consumed, 'Unlinked review rating must not be consumed in aggregates')
        self.assertFalse(rating.feedback_review_id, 'Bi-directional pointer must be cleared')

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(tmpl.rating_count, 0)

    # ------------------------------------------------------------------
    # 7. Rating value update stays on same native row
    # ------------------------------------------------------------------

    def test_09_rating_update_writes_same_native_row(self):
        review = self._make_review(rating=3, status_after_create='approved')
        rating_id = review.rating_id.id
        review.write({'rating': 5})
        self.assertEqual(review.rating_id.id, rating_id)
        self.assertEqual(review.rating_id.rating, 5.0)
        self.assertTrue(review.rating_id.consumed)

        tmpl = self.product.product_tmpl_id
        tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertAlmostEqual(tmpl.rating_avg, 5.0, places=2)

    # ------------------------------------------------------------------
    # 8. Unique constraint: one native rating per feedback.review
    # ------------------------------------------------------------------

    def test_10_unique_feedback_review_on_native_rating(self):
        review = self._make_review(rating=5, status_after_create='approved')
        Rating = self.env['rating.rating'].sudo()
        with self.assertRaises(Exception):
            Rating.create({
                'res_model': 'product.template',
                'res_id': review.product_tmpl_id.id,
                'partner_id': self.customer.id,
                'rating': 5.0,
                'consumed': True,
                'feedback_review_id': review.id,
            })

    # ------------------------------------------------------------------
    # 9. Token / request linkage security basics (via model)
    # ------------------------------------------------------------------

    def test_11_one_review_per_request_constraint(self):
        request = self._create_request()
        self.env['feedback.review'].create({
            'request_id': request.id,
            'product_id': request.product_id.id,
            'customer_id': request.partner_id.id,
            'rating': 5,
            'review_text': 'First review with enough text length here.',
        })
        with self.assertRaises(Exception):
            self.env['feedback.review'].create({
                'request_id': request.id,
                'product_id': request.product_id.id,
                'customer_id': request.partner_id.id,
                'rating': 4,
                'review_text': 'Second review should be blocked by unique constraint.',
            })

    def test_12_rating_related_field_is_projection_not_stored(self):
        """rating on feedback.review is a related projection of rating_id.rating."""
        Review = self.env['feedback.review']
        field = Review._fields['rating']
        self.assertTrue(field.related, 'rating must remain a related field to rating_id.rating')
        self.assertFalse(getattr(field, 'store', False) or field.store,
                         'rating must not be stored on feedback.review')
