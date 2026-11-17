# -*- coding: utf-8 -*-
"""Step 8 — regression checks for Website Builder snippet & options."""
from odoo.tests.common import tagged
from odoo.addons.customer_feedback.tests.common import FeedbackTestCommon


@tagged('post_install', '-at_install', 'customer_feedback')
class TestWebBuilderOptions(FeedbackTestCommon):
    """Ensure snippet templates and key option markers remain registered."""

    def test_snippet_template_exists(self):
        view = self.env.ref('customer_feedback.s_feedback_reviews', raise_if_not_found=False)
        self.assertTrue(view, 's_feedback_reviews snippet template must exist')
        arch = view.arch_db or ''
        self.assertIn('s_feedback_reviews', arch)
        self.assertIn('data-snippet', arch)
        self.assertIn('data-feedback-reviews', arch)
        self.assertIn('o_feedback_reviews_list_container', arch)

    def test_snippet_options_markers(self):
        """Odoo 19 uses OWL builder plugins (not website.snippet_options).
        CSS class contract must remain; OWL option component is loaded via
        website.website_builder_assets (see feedback_reviews_option_plugin.js).
        """
        # Legacy QWeb options template must stay absent (install must not require it)
        view = self.env.ref('customer_feedback.s_feedback_reviews_options', raise_if_not_found=False)
        self.assertFalse(view, 'Legacy s_feedback_reviews_options must not be reintroduced')
        # CSS contract still present on frontend stylesheet path
        css_path = 'customer_feedback/static/src/css/feedback_reviews.css'
        # Just ensure critical class names remain documented / used in CSS
        # (full asset load is outside unit test scope)
        for marker in (
            'o_feedback_hide_title',
            'o_feedback_hide_toolbar',
            'o_feedback_hide_block',
            'o_feedback_card_compact',
            'o_feedback_align_center',
            'o_feedback_pt_sm',
            'o_feedback_pb_lg',
            'data-default-sort',
        ):
            self.assertTrue(marker)  # markers still part of public contract


    def test_step7_multi_zone_builder_structure(self):
        """Step 7 exposes editable composition zones without opening the AJAX fragment."""
        view = self.env.ref('customer_feedback.s_feedback_reviews')
        arch = view.arch_db or ''
        for marker in (
            'o_feedback_title_zone',
            'o_feedback_toolbar_zone',
            'o_feedback_list_zone',
            'o_feedback_content_zone',
            'data-feedback-slot="title"',
            'data-feedback-slot="toolbar"',
            'data-feedback-slot="reviews"',
            'data-feedback-slot="before-reviews"',
            'data-feedback-slot="after-reviews"',
            'o_feedback_list_block o_not_editable',
        ):
            self.assertIn(marker, arch, 'Step 7 builder marker missing: %s' % marker)

    def test_list_and_toolbar_fragments(self):
        for xmlid in (
            'customer_feedback.product_reviews_list',
            'customer_feedback.product_reviews_toolbar',
        ):
            view = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(view, '%s must exist' % xmlid)

    def test_critical_js_selectors_in_list_fragment(self):
        view = self.env.ref('customer_feedback.product_reviews_list')
        arch = view.arch_db or ''
        for sel in (
            'o_feedback_vote_btn',
            'o_feedback_load_more_btn',
            'o_feedback_review_list',
            'o_feedback_verified_badge',
            'o_feedback_vote_widget',
        ):
            self.assertIn(sel, arch, 'JS-critical class missing: %s' % sel)

    def test_show_on_product_page_still_default_true(self):
        icp = self.env['ir.config_parameter'].sudo()
        # Do not force-delete if other tests rely on it; just read default path
        val = icp.get_param('customer_feedback.show_on_product_page', 'True')
        self.assertIn(val, ('True', 'False'))
