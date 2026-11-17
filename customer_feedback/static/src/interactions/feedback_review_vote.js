/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Handles Helpful / Not Helpful votes, and the sort/star-filter toolbar, on
 * published product reviews. Uses Odoo 19 Interaction (replaces legacy
 * publicWidget). Both concerns live in one Interaction because they share
 * the same root element (.s_feedback_reviews) and Interaction's
 * dynamicContent event delegation is attached once per matched root, not
 * per DOM node - so newly-fetched review cards (after a sort/filter
 * refresh) are still handled by the same delegated ".o_feedback_vote_btn"
 * listener below without any extra rebinding step.
 */
export class FeedbackReviewVote extends Interaction {
    static selector = ".s_feedback_reviews, .o_feedback_reviews_wrapper, #o_feedback_reviews";

    dynamicContent = {
        ".o_feedback_vote_btn": {
            "t-on-click.prevent.withTarget": this.onVoteClick,
        },
        ".o_feedback_sort_select": {
            "t-on-change.withTarget": this.onToolbarChange,
        },
        ".o_feedback_star_filter_btn": {
            "t-on-click.prevent.withTarget": this.onStarFilterClick,
        },
        ".o_feedback_load_more_btn": {
            "t-on-click.prevent.withTarget": this.onLoadMoreClick,
        },
    };

    setup() {
        // Multi-select set of active star filters, e.g. {5, 4}. Kept in
        // memory on the Interaction instance so it survives a list refresh
        // (the toolbar itself is never replaced, only the list below it).
        this.activeStars = new Set();
        // Step 5 — self-heal defensive check: if the editor (duplicate,
        // copy/paste, undo/redo, or a manual HTML edit) ever leaves this
        // page with two elements sharing a critical id, fix it before any
        // vote/sort/filter/load-more listener fires. This mirrors the
        // build-time fix in feedback_reviews_option_plugin.js so the page
        // is safe even if the builder-time hook didn't run (e.g. content
        // imported from another database, or restored from an old backup).
        this._selfHealDuplicateIds();
        // Step 6 — apply Website Builder "Default sort" if set on the section
        // (data-default-sort from snippet option). Only runs once on load;
        // does not change vote/sort/filter behaviour otherwise.
        this._applyDefaultSortFromSnippet();
    }

    /**
     * Rewrites this instance's critical ids with a unique suffix whenever
     * they collide with another element already on the page, and keeps
     * the sort <label for="..."> in sync. Safe no-op for the normal
     * single-instance case. Never touches classes, data-* attributes, or
     * anything the vote/sort/filter/load-more handlers rely on for
     * behaviour — only ids used for accessibility/label association and
     * for legacy #id lookups.
     */
    _selfHealDuplicateIds() {
        const root = this.el;
        if (!root) {
            return;
        }
        const section = root.classList.contains("s_feedback_reviews")
            ? root
            : root.closest(".s_feedback_reviews");
        if (!section) {
            return;
        }
        const criticalIds = [
            "o_feedback_reviews_list_container",
            "o_feedback_reviews",
            "o_feedback_sort_select",
        ];
        for (const baseId of criticalIds) {
            const el = section.querySelector(`#${baseId}`);
            if (!el) {
                continue;
            }
            if (document.querySelectorAll(`#${baseId}`).length <= 1) {
                continue;
            }
            const newId = `${baseId}_${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`;
            el.id = newId;
            if (baseId === "o_feedback_sort_select") {
                const label = section.querySelector(`label[for="${baseId}"]`);
                if (label) {
                    label.setAttribute("for", newId);
                }
            }
        }
    }

    /**
     * If the reviews section has data-default-sort (newest|highest|lowest)
     * from the Website Builder option, select that value in the toolbar.
     * Does not auto-refresh the list (server already rendered newest by
     * default); user can change sort afterwards as usual.
     */
    _applyDefaultSortFromSnippet() {
        const root = this.el;
        if (!root) {
            return;
        }
        const section = root.classList.contains("s_feedback_reviews")
            ? root
            : root.closest(".s_feedback_reviews");
        if (!section) {
            return;
        }
        const defaultSort = section.getAttribute("data-default-sort");
        if (!defaultSort || !["newest", "highest", "lowest"].includes(defaultSort)) {
            return;
        }
        const sortSelect = section.querySelector(".o_feedback_sort_select");
        if (!sortSelect) {
            return;
        }
        if (sortSelect.value !== defaultSort) {
            sortSelect.value = defaultSort;
            // Refresh list only when default is not newest (server render is newest)
            if (defaultSort !== "newest") {
                this.refreshReviewList(sortSelect);
            }
        }
    }

    async onStarFilterClick(ev, currentTargetEl) {
        const rating = currentTargetEl.getAttribute("data-rating");
        if (!rating) {
            return;
        }
        if (this.activeStars.has(rating)) {
            this.activeStars.delete(rating);
            currentTargetEl.classList.remove("active", "btn-secondary");
            currentTargetEl.classList.add("btn-outline-secondary");
        } else {
            this.activeStars.add(rating);
            currentTargetEl.classList.add("active", "btn-secondary");
            currentTargetEl.classList.remove("btn-outline-secondary");
        }
        await this.refreshReviewList(currentTargetEl);
    }

    async onToolbarChange(ev, currentTargetEl) {
        await this.refreshReviewList(currentTargetEl);
    }

    async onLoadMoreClick(ev, currentTargetEl) {
        const toolbar = currentTargetEl.closest(".s_feedback_reviews, .o_feedback_reviews_wrapper");
        if (!toolbar || currentTargetEl.disabled) {
            return;
        }
        const container = toolbar.querySelector("#o_feedback_reviews_list_container");
        if (!container) {
            return;
        }
        const productId = container.getAttribute("data-product-id");
        const section = container.querySelector("#o_feedback_reviews");
        const offset = currentTargetEl.getAttribute("data-offset") || (section && section.getAttribute("data-next-offset")) || "0";
        if (!productId) {
            return;
        }

        const sortSelect = toolbar.querySelector(".o_feedback_sort_select");
        const sort = sortSelect ? sortSelect.value : "newest";
        const params = new URLSearchParams({ sort, offset, limit: "20" });
        if (this.activeStars.size) {
            params.set("rating", Array.from(this.activeStars).join(","));
        }

        currentTargetEl.disabled = true;
        try {
            const response = await fetch(
                `/feedback/product/${encodeURIComponent(productId)}/reviews?${params.toString()}`
            );
            if (!response.ok) {
                currentTargetEl.disabled = false;
                return;
            }
            const html = await response.text();
            const doc = new DOMParser().parseFromString(html, "text/html");
            const incomingList = doc.querySelector(".o_feedback_review_list");
            const currentList = container.querySelector(".o_feedback_review_list");
            if (incomingList && currentList) {
                while (incomingList.firstElementChild) {
                    currentList.appendChild(incomingList.firstElementChild);
                }
            }
            const incomingButton = doc.querySelector(".o_feedback_load_more_btn");
            if (incomingButton) {
                currentTargetEl.replaceWith(incomingButton);
            } else {
                currentTargetEl.closest("div.text-center")?.remove();
            }
        } catch (error) {
            currentTargetEl.disabled = false;
            console.warn("Feedback review load-more failed", error);
        }
    }

    async refreshReviewList(fromEl) {
        const toolbar = fromEl.closest(".s_feedback_reviews, .o_feedback_reviews_wrapper");
        if (!toolbar) {
            return;
        }
        const container = toolbar.querySelector("#o_feedback_reviews_list_container");
        if (!container) {
            return;
        }
        const productId = container.getAttribute("data-product-id");
        if (!productId) {
            return;
        }
        const sortSelect = toolbar.querySelector(".o_feedback_sort_select");
        const sort = sortSelect ? sortSelect.value : "newest";

        const params = new URLSearchParams({ sort, limit: "20", offset: "0" });
        if (this.activeStars.size) {
            params.set("rating", Array.from(this.activeStars).join(","));
        }

        try {
            const response = await fetch(
                `/feedback/product/${encodeURIComponent(productId)}/reviews?${params.toString()}`
            );
            if (!response.ok) {
                return;
            }
            const html = await response.text();
            container.innerHTML = html;
            // Step 6 — the fragment just injected re-renders #o_feedback_reviews
            // with its plain, unsuffixed id. If a second instance of this
            // snippet exists on the same page, restore id-uniqueness right
            // away so a subsequent edit/duplicate elsewhere doesn't get
            // confused about which #o_feedback_reviews is which.
            this._selfHealDuplicateIds();
        } catch (error) {
            // Silent fail – sort/filter is progressive enhancement, the
            // unfiltered list already rendered server-side stays visible.
            console.warn("Feedback review list refresh failed", error);
        }
    }

    async onVoteClick(ev, currentTargetEl) {
        const btn = currentTargetEl;
        const reviewId = btn.getAttribute("data-review-id");
        const voteType = btn.getAttribute("data-vote-type");
        if (!reviewId || !voteType) {
            return;
        }

        const widget = btn.closest(".o_feedback_vote_widget");
        if (!widget) {
            return;
        }

        // Prevent double-clicks while the request is in flight
        if (btn.disabled) {
            return;
        }
        btn.disabled = true;

        try {
            const response = await fetch(`/feedback/review/${reviewId}/vote`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: `vote_type=${encodeURIComponent(voteType)}`,
            });
            const data = await response.json();
            if (data.error) {
                return;
            }
            const helpfulEl = widget.querySelector(".o_helpful_count");
            const notHelpfulEl = widget.querySelector(".o_not_helpful_count");
            if (helpfulEl) {
                helpfulEl.textContent = data.helpful_count;
            }
            if (notHelpfulEl) {
                notHelpfulEl.textContent = data.not_helpful_count;
            }
        } catch (error) {
            // Silent fail – voting is non-critical UX
            console.warn("Feedback vote failed", error);
        } finally {
            btn.disabled = false;
        }
    }
}

registry
    .category("public.interactions")
    .add("customer_feedback.feedback_review_vote", FeedbackReviewVote);
