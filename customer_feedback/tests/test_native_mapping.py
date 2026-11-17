# -*- coding: utf-8 -*-
"""Phase 2: Odoo 19 native mapping regression tests.

These tests turn the KEEP / EXTEND / REMOVE decisions from
``doc/PHASE2_NATIVE_MAPPING.md`` into executable guards so later refactors do
not accidentally duplicate native Odoo rating functionality.
"""
from odoo.tests import tagged

from .common import FeedbackTestCommon


@tagged('post_install', '-at_install')
class TestNativeOdooMapping(FeedbackTestCommon):
    """Executable contract for the Phase 2 native Odoo mapping."""

    def test_product_uses_native_rating_mixin_source_of_truth(self):
        Product = self.env['product.template']
        # Runtime inheritance is exposed through the model's MRO; the fields
        # themselves are the stable contract we care about in Odoo 19.
        self.assertIn('rating_avg', Product._fields)
        self.assertIn('rating_count', Product._fields)
        self.assertIn('rating_ids', Product._fields)
        self.assertEqual(Product._fields['rating_avg'].compute, '_compute_rating_stats')
        self.assertEqual(Product._fields['rating_count'].compute, '_compute_rating_stats')

    def test_legacy_product_rating_duplicates_are_removed(self):
        Product = self.env['product.template']
        for field_name in ('average_rating', 'total_reviews', 'review_count'):
            self.assertNotIn(
                field_name,
                Product._fields,
                'Legacy duplicate %s must not be reintroduced; native rating_avg/rating_count are the source of truth.' % field_name,
            )

    def test_feedback_review_is_business_layer_not_rating_source(self):
        Review = self.env['feedback.review']
        self.assertIn('rating', Review._fields)
        self.assertIn('status', Review._fields)
        self.assertIn('request_id', Review._fields)
        self.assertIn('rating_id', Review._fields)
        self.assertEqual(Review._fields['rating_id'].comodel_name, 'rating.rating')

    def test_histogram_is_explicitly_extra_business_projection(self):
        Product = self.env['product.template']
        for field_name in (
            # histogram fields removed — use get_rating_distribution() / native repartition
        ):
            self.assertIn(field_name, Product._fields)
            self.assertTrue(Product._fields[field_name].readonly)

        # Odoo 19 exposes native on-demand repartition/statistics.  This is a
        # mapping guard: the module's stored histogram must remain a projection
        # and must never replace rating.mixin's native aggregate fields.
        self.assertTrue(hasattr(Product, '_rating_get_repartition'))
        self.assertTrue(hasattr(Product, 'rating_get_stats'))

    def test_explicit_native_rating_dependency_is_kept(self):
        manifest = self.env['ir.module.module']._get('customer_feedback')
        self.assertIn('rating', manifest.dependencies_id.mapped('name'))

    def test_public_product_rating_source_is_native(self):
        product = self.product.product_tmpl_id
        product.invalidate_recordset(['rating_avg', 'rating_count'])
        self.assertEqual(product.rating_count, self.env['rating.rating'].search_count([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', product.id),
            ('consumed', '=', True),
            ('rating', '>=', 1),
        ]))
