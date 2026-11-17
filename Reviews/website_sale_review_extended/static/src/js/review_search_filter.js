/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { whenReady } from "@odoo/owl";

/**
 * Review search bar + quick filters (Phase 4) on the product page.
 *
 * Self-bootstraps on DOM ready, the same way review_variant_filter.js
 * does (no publicWidget dependency), and reuses the exact same
 * "hide/show message DOM nodes by allowed message id" strategy so both
 * scripts stay consistent even though they run independently.
 *
 * Wired to a single call: /website_sale/review/search, which folds the
 * text query, "with images only" and "minimum stars" quick filters into
 * one server-side domain (product.template.search_reviews()). When the
 * "This variant only" toggle from review_variant_filter.js is present
 * and checked, its state is read and forwarded too, so the two filters
 * compose instead of fighting over the same DOM nodes.
 */

const DEBOUNCE_MS = 350;

function resolveTemplateId() {
    const el = document.querySelector(
        "[data-res-model='product.template'][data-res-id], [data-product-template-id], input[name='product_template_id']"
    );
    if (el) {
        const v =
            el.getAttribute("data-res-id") ||
            el.getAttribute("data-product-template-id") ||
            el.value;
        const n = parseInt(v, 10);
        if (n) return n;
    }
    const m = window.location.pathname.match(/-(\d+)\/?$/);
    if (m) return parseInt(m[1], 10);
    return null;
}

function resolveVariantState() {
    // Read the Phase 2 toggle if it's on the page; otherwise search
    // simply ignores variant restriction.
    const toggle = document.querySelector(".o_wsre_variant_only_toggle");
    const productInput = document.querySelector(
        ".js_product input[name='product_id'], #product_form input[name='product_id'], input[name='product_id']"
    );
    const productId = productInput?.value ? parseInt(productInput.value, 10) || null : null;
    return {
        variantOnly: !!(toggle && toggle.checked && productId),
        productId,
    };
}

function hasReviewArea() {
    return !!document.querySelector(
        ".o_portal_chatter, .o_message_counter, [data-res-model='product.template']"
    );
}

function injectSearchBar() {
    if (document.querySelector(".o_wsre_search_bar")) {
        return document.querySelector(".o_wsre_search_bar");
    }
    const anchor =
        document.querySelector(".o_wsre_variant_filter_bar") ||
        document.querySelector(".o_portal_chatter");
    const bar = document.createElement("div");
    bar.className = "o_wsre_search_bar mb-3";
    bar.innerHTML = `
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <input type="search" class="form-control form-control-sm o_wsre_search_input"
                   style="max-width:260px;" placeholder="Search reviews…"/>
            <div class="form-check mb-0">
                <input type="checkbox" class="form-check-input o_wsre_images_only" id="o_wsre_images_only"/>
                <label class="form-check-label small" for="o_wsre_images_only">With images only</label>
            </div>
            <div class="btn-group btn-group-sm o_wsre_star_filter" role="group" aria-label="Filter by stars">
                <button type="button" class="btn btn-outline-secondary active" data-min-stars="0">All</button>
                <button type="button" class="btn btn-outline-secondary" data-min-stars="4">4+ <i class="fa fa-star text-warning"/></button>
                <button type="button" class="btn btn-outline-secondary" data-min-stars="3">3+ <i class="fa fa-star text-warning"/></button>
                <button type="button" class="btn btn-outline-secondary" data-min-stars="1">1+ <i class="fa fa-star text-warning"/></button>
            </div>
            <span class="o_wsre_search_stats text-muted small"></span>
        </div>
    `;
    const variantBar = document.querySelector(".o_wsre_variant_filter_bar");
    if (anchor && anchor.parentNode) {
        if (variantBar) {
            // Insert right after the Phase 2 "This variant only" bar.
            anchor.parentNode.insertBefore(bar, variantBar.nextSibling);
        } else {
            // No variant bar on this page: insert before the chatter itself.
            anchor.parentNode.insertBefore(bar, anchor);
        }
    } else {
        const main = document.querySelector("main, #wrap, .oe_structure");
        if (main) main.prepend(bar);
        else return null;
    }
    return bar;
}

function applyAllowedSet(messageIds) {
    const allowed = messageIds === null ? null : new Set(messageIds);
    const messages = document.querySelectorAll(
        ".o-mail-Message, .o_portal_chatter_message, [data-message-id], .o_message"
    );
    messages.forEach((node) => {
        const mid =
            parseInt(node.getAttribute("data-message-id"), 10) ||
            parseInt(node.dataset?.messageId, 10) ||
            parseInt(node.dataset?.id, 10) ||
            null;
        if (allowed === null) {
            node.classList.remove("d-none");
            node.style.removeProperty("display");
            return;
        }
        if (mid && allowed.has(mid)) {
            node.classList.remove("d-none");
            node.style.removeProperty("display");
        } else if (mid) {
            node.classList.add("d-none");
        }
    });
}

async function runSearch(bar) {
    const tmplId = resolveTemplateId();
    if (!tmplId) return;

    const statsEl = bar.querySelector(".o_wsre_search_stats");
    const query = bar.querySelector(".o_wsre_search_input")?.value?.trim() || "";
    const withImagesOnly = !!bar.querySelector(".o_wsre_images_only")?.checked;
    const activeStarBtn = bar.querySelector(".o_wsre_star_filter .active");
    const minStars = parseInt(activeStarBtn?.getAttribute("data-min-stars") || "0", 10);
    const { variantOnly, productId } = resolveVariantState();

    // Nothing active → show everything, skip the round-trip.
    if (!query && !withImagesOnly && !minStars && !variantOnly) {
        applyAllowedSet(null);
        if (statsEl) statsEl.textContent = "";
        return;
    }

    if (statsEl) statsEl.textContent = "Searching…";

    let result;
    try {
        result = await rpc("/website_sale/review/search", {
            product_tmpl_id: tmplId,
            query,
            product_id: productId,
            variant_only: variantOnly,
            min_stars: minStars,
            with_images_only: withImagesOnly,
            limit: 50,
            offset: 0,
        });
    } catch (e) {
        if (statsEl) statsEl.textContent = "";
        return;
    }
    if (!result?.ok) {
        if (statsEl) statsEl.textContent = "";
        return;
    }

    applyAllowedSet(result.message_ids || []);
    if (statsEl) {
        statsEl.textContent = result.total
            ? `${result.total} review${result.total === 1 ? "" : "s"} found`
            : "No reviews match your filters";
    }
}

function debounce(fn, ms) {
    let timer = null;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

function bindEvents(bar) {
    const debouncedSearch = debounce(() => runSearch(bar), DEBOUNCE_MS);

    bar.querySelector(".o_wsre_search_input")?.addEventListener("input", debouncedSearch);

    bar.querySelector(".o_wsre_images_only")?.addEventListener("change", () => runSearch(bar));

    bar.querySelectorAll(".o_wsre_star_filter button").forEach((btn) => {
        btn.addEventListener("click", () => {
            bar.querySelectorAll(".o_wsre_star_filter button").forEach((b) =>
                b.classList.remove("active")
            );
            btn.classList.add("active");
            runSearch(bar);
        });
    });

    // Re-run when the variant toggle changes, so the two filters compose.
    document.addEventListener("change", (ev) => {
        if (ev.target?.matches?.(".o_wsre_variant_only_toggle")) {
            runSearch(bar);
        }
    });
}

function boot() {
    if (!hasReviewArea()) return;
    if (!resolveTemplateId()) return;
    const bar = injectSearchBar();
    if (!bar) return;
    bindEvents(bar);
}

whenReady(() => {
    // Run after review_variant_filter.js's own bootstrap so we can
    // anchor next to its bar when present.
    setTimeout(boot, 400);
});
