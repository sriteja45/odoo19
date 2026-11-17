# -*- coding: utf-8 -*-
"""Steps 4–6 — Web Builder hardening regression checks.

Step 4: editor placeholder stays intact, and a genuine sibling "drop
        zone" exists for supplementary content, outside the protected
        AJAX list container.
Step 5: the ids that feedback_review_vote.js and the sort <label> rely
        on are still present in the template, and the option plugin
        exposes the duplicate-id self-heal used when a snippet instance
        is dropped or cloned in the builder.
Step 6: the AJAX refresh path (server fragment + client-side JS) keeps
        those same ids/classes after a sort/filter/load-more round trip,
        and the self-heal hook is invoked after every refresh so two
        instances of the snippet on one page never end up with
        colliding ids.

These are static/template-contract tests (no live editor/browser), in
keeping with the rest of this module's test suite — they protect the
markup contract that the JS in static/src depends on.
"""
import re

from odoo.tests.common import tagged
from odoo.addons.customer_feedback.tests.common import FeedbackTestCommon


@tagged('post_install', '-at_install', 'customer_feedback')
class TestWebBuilderHardening(FeedbackTestCommon):

    # ---------------------------------------------------------------
    # Step 4 — editor placeholder + drop zone
    # ---------------------------------------------------------------
    def test_placeholder_stays_not_editable(self):
        """The no-product placeholder must remain o_not_editable: it
        mirrors the exact AJAX-rendered DOM, so it must not be
        hand-edited by mistake."""
        view = self.env.ref('customer_feedback.s_feedback_reviews')
        arch = view.arch_db or ''
        self.assertIn('o_feedback_editor_placeholder', arch)
        # placeholder div itself carries o_not_editable
        match = re.search(
            r'class="o_feedback_editor_placeholder[^"]*o_not_editable[^"]*"',
            arch,
        )
        self.assertTrue(match, 'Editor placeholder must stay o_not_editable')

    def test_drop_zone_is_sibling_of_protected_container(self):
        """The supplementary drop zone must exist, be editable, and be
        a SIBLING of #o_feedback_reviews_list_container — never nested
        inside it — so an AJAX refresh can never wipe it."""
        view = self.env.ref('customer_feedback.s_feedback_reviews')
        arch = view.arch_db or ''
        self.assertIn('o_feedback_extra_content', arch)
        self.assertIn('o_editable', arch)

        list_container_close = arch.find('id="o_feedback_reviews_list_container"')
        self.assertNotEqual(list_container_close, -1)
        # Find the closing </div> of the list container block and make sure
        # the drop zone marker only appears AFTER it (sibling-level), not
        # inside the container's own subtree.
        extra_pos = arch.find('o_feedback_extra_content')
        self.assertGreater(
            extra_pos, list_container_close,
            'Drop zone must be declared after (sibling of) the protected list container',
        )

    def test_drop_zone_starts_empty(self):
        """Ships empty by default: zero visible/behavioural change for
        existing sites until an editor deliberately adds content."""
        view = self.env.ref('customer_feedback.s_feedback_reviews')
        arch = view.arch_db or ''
        self.assertRegex(
            arch,
            r'<div class="o_feedback_extra_content o_editable" data-feedback-dropzone="1"\s*/>',
            'Drop zone should render as a self-closing, empty element by default',
        )

    # ---------------------------------------------------------------
    # Step 5 — protected JS hooks
    # ---------------------------------------------------------------
    def test_critical_ids_present_in_snippet(self):
        view = self.env.ref('customer_feedback.s_feedback_reviews')
        arch = view.arch_db or ''
        for critical_id in (
            'id="o_feedback_reviews_list_container"',
        ):
            self.assertIn(critical_id, arch)

    def test_critical_ids_present_in_fragments(self):
        list_view = self.env.ref('customer_feedback.product_reviews_list')
        toolbar_view = self.env.ref('customer_feedback.product_reviews_toolbar')
        list_arch = list_view.arch_db or ''
        toolbar_arch = toolbar_view.arch_db or ''
        self.assertIn('id="o_feedback_reviews"', list_arch)
        self.assertIn('id="o_feedback_sort_select"', toolbar_arch)
        self.assertIn('for="o_feedback_sort_select"', toolbar_arch)

    def test_option_plugin_exposes_id_self_heal(self):
        """The Website Builder plugin must wire up the duplicate-id
        self-heal on both drop and clone, so a snippet instance can
        never leave the page with colliding ids after those actions."""
        import os
        plugin_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'src', 'builder', 'plugins',
            'feedback_reviews_option_plugin.js',
        )
        with open(plugin_path, encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn('_makeIdsUnique', content)
        self.assertIn('on_snippet_dropped_handlers', content)
        self.assertIn('on_cloned_handlers', content)

    def test_vote_js_has_runtime_self_heal(self):
        """Defense in depth: the Interaction itself re-checks for
        duplicate ids on setup and after every AJAX refresh, in case
        content ever reaches the page without going through the
        builder hooks above (import, restore, manual edit, etc.)."""
        import os
        js_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'src', 'interactions', 'feedback_review_vote.js',
        )
        with open(js_path, encoding='utf-8') as fh:
            content = fh.read()
        self.assertIn('_selfHealDuplicateIds', content)
        # Called once on setup...
        self.assertIn('this._selfHealDuplicateIds();', content)
        # ...and again after the sort/filter AJAX refresh rewrites the
        # container's innerHTML (which reintroduces the plain, unsuffixed
        # ids from the server fragment).
        refresh_method_start = content.find('async refreshReviewList')
        self.assertNotEqual(refresh_method_start, -1)
        self.assertIn(
            '_selfHealDuplicateIds',
            content[refresh_method_start:],
            'refreshReviewList must re-run the self-heal after replacing innerHTML',
        )

    # ---------------------------------------------------------------
    # Step 6 — AJAX reload safety after builder edits
    # ---------------------------------------------------------------
    def test_ajax_target_classes_unchanged_by_customize_options(self):
        """Visibility/layout options are all applied via classes on the
        outer .s_feedback_reviews section (see feedback_reviews_option.xml),
        never on the AJAX-managed fragment. This is what allows a full
        sort/filter/load-more refresh (container.innerHTML replacement)
        to happen without ever touching, or being undone by, a builder
        style choice."""
        list_view = self.env.ref('customer_feedback.product_reviews_list')
        arch = list_view.arch_db or ''
        # The fragment must not itself declare any of the hide/layout
        # option classes — those only ever live on the ancestor section.
        for option_class in (
            'o_feedback_hide_title',
            'o_feedback_hide_toolbar',
            'o_feedback_card_compact',
        ):
            self.assertNotIn(
                option_class, arch,
                'Customize option classes must stay on .s_feedback_reviews, '
                'not on the AJAX-replaced fragment (%s found in fragment)' % option_class,
            )

    def test_snippet_registered_after_hardening(self):
        """Sanity check that the snippet registration itself (used by
        the builder's snippet panel) was not broken by the Step 4–6
        changes."""
        view = self.env.ref('customer_feedback.snippets', raise_if_not_found=False)
        self.assertTrue(view, 'Website Builder snippet registration must remain intact')
        arch = view.arch_db or ''
        self.assertIn('customer_feedback.s_feedback_reviews', arch)
