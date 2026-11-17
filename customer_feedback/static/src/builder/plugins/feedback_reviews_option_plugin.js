/** @odoo-module **/

/**
 * Odoo 19 Website Builder options for the Customer Reviews snippet
 * (s_feedback_reviews).
 *
 * Steps 1–3: improved nested editable structure.
 * Step 4: editor placeholder + safe "drop zone" for extra content.
 * Step 5: protect JS hooks (ids/data-attrs) so duplicating/editing the
 *         snippet in the builder can never create colliding ids that
 *         would confuse the vote/sort/filter/load-more Interaction.
 * Step 6: AJAX-reload safety net after structural edits in the builder.
 *
 * Only adds visual / class-based Customize panel controls plus the
 * defensive id-hygiene below. Does NOT change votes, sort/filter,
 * load-more, moderation, rating bridge, token flow or any backend
 * behaviour.
 */

import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class FeedbackReviewsOption extends BaseOptionComponent {
    static template = "customer_feedback.FeedbackReviewsOption";
    static selector = ".s_feedback_reviews";
}

/**
 * Secondary option for the title block so it is easier to select
 * and style independently in the Website Builder.
 */
export class FeedbackReviewsTitleOption extends BaseOptionComponent {
    static template = "customer_feedback.FeedbackReviewsTitleOption";
    static selector = ".s_feedback_reviews .o_feedback_title_block";
}

/**
 * Step 5 — Protect critical JS hooks.
 *
 * The list container (#o_feedback_reviews_list_container), the AJAX
 * target (#o_feedback_reviews) and the sort <select>/<label> pair
 * (#o_feedback_sort_select) are shipped with fixed ids so the template
 * renders correctly out of the box. But the Website Builder lets an
 * editor "Duplicate" the whole section, or copy/paste it onto another
 * page. That produces two elements sharing the same id on one page,
 * which breaks id-based lookups and label/for associations even though
 * the vote/sort/filter code itself is careful to scope its queries to
 * the closest ancestor.
 *
 * `_makeIdsUnique` runs whenever a snippet instance is dropped/built
 * and rewrites those ids to a per-instance suffix, keeping the
 * "for"/"id" pairing intact. It is idempotent and a no-op on a page
 * that only has a single instance (the default, most common case), so
 * there is zero visible change to existing sites.
 */
function _makeIdsUnique(sectionEl) {
    if (!sectionEl || !sectionEl.classList.contains("s_feedback_reviews")) {
        return;
    }
    const suffix = `_${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`;
    const idMap = {
        o_feedback_reviews_list_container: null,
        o_feedback_reviews: null,
        o_feedback_sort_select: null,
    };

    for (const baseId of Object.keys(idMap)) {
        const el = sectionEl.querySelector(`#${baseId}`);
        if (!el) {
            continue;
        }
        // Only rewrite if this id is already used elsewhere on the page
        // (i.e. this is a duplicate) — leaves the first/only instance
        // with its original, human-readable id.
        const clashes = document.querySelectorAll(`#${baseId}`).length > 1;
        if (!clashes) {
            continue;
        }
        const newId = `${baseId}${suffix}`;
        el.id = newId;
        idMap[baseId] = newId;
    }

    if (idMap.o_feedback_sort_select) {
        const label = sectionEl.querySelector('label[for="o_feedback_sort_select"]');
        if (label) {
            label.setAttribute("for", idMap.o_feedback_sort_select);
        }
    }
}

export class FeedbackReviewsOptionPlugin extends Plugin {
    static id = "customerFeedbackReviewsOption";
    resources = {
        builder_options: [
            FeedbackReviewsOption,
            FeedbackReviewsTitleOption,
        ],
        // Step 5/6 — run id-hygiene right after the snippet is dropped
        // (fresh drag from the panel) and again after it is cloned via
        // the builder's "Duplicate" action, which is the scenario that
        // actually produces colliding ids.
        on_snippet_dropped_handlers: (el) => _makeIdsUnique(el),
        on_cloned_handlers: (el) => _makeIdsUnique(el),
    };
}

registry.category("website-plugins").add(
    FeedbackReviewsOptionPlugin.id,
    FeedbackReviewsOptionPlugin
);

// Exported for unit testing (Step 6 regression coverage) and reuse by
// the runtime self-heal guard in feedback_review_vote.js.
export { _makeIdsUnique };
