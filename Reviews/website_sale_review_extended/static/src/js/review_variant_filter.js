/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { whenReady } from "@odoo/owl";

/**
 * "This variant only" toggle on the product page review section.
 *
 * Wires to query param `wsre_variant_only=1` and optional `product_id`.
 * Calls /website_sale/review/filter and shows/hides message DOM nodes.
 * Self-bootstraps on DOM ready (no publicWidget dependency — safer across
 * Odoo 19 point releases).
 */

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

function resolveProductId() {
    const el = document.querySelector(
        ".js_product input[name='product_id'], #product_form input[name='product_id'], input[name='product_id']"
    );
    if (el?.value) {
        const n = parseInt(el.value, 10);
        if (n) return n;
    }
    try {
        const u = new URL(window.location.href);
        const q = u.searchParams.get("product_id");
        if (q) return parseInt(q, 10) || null;
    } catch (_) {}
    return null;
}

function hasReviewArea() {
    return !!(
        document.querySelector(
            ".o_portal_chatter, .o_message_counter, [data-res-model='product.template']"
        )
    );
}

function injectToggle() {
    if (document.querySelector(".o_wsre_variant_filter_bar")) {
        return document.querySelector(".o_wsre_variant_only_toggle");
    }
    const chatter =
        document.querySelector(".o_portal_chatter") ||
        document.querySelector(".o_wsre_review_extra")?.closest?.(".o_portal_chatter");
    const bar = document.createElement("div");
    bar.className =
        "o_wsre_variant_filter_bar form-check mb-2 d-flex align-items-center gap-2";
    bar.innerHTML = `
        <input type="checkbox" class="form-check-input o_wsre_variant_only_toggle" id="o_wsre_variant_only"/>
        <label class="form-check-label small" for="o_wsre_variant_only">
            This variant only
        </label>
        <span class="o_wsre_variant_filter_stats text-muted small"></span>
    `;
    if (chatter && chatter.parentNode) {
        chatter.parentNode.insertBefore(bar, chatter);
    } else {
        const main = document.querySelector("main, #wrap, .oe_structure");
        if (main) main.prepend(bar);
        else return null;
    }
    return bar.querySelector(".o_wsre_variant_only_toggle");
}

async function applyFilter(variantOnly) {
    const tmplId = resolveTemplateId();
    const productId = resolveProductId();
    if (!tmplId) return;

    const statsEl = document.querySelector(".o_wsre_variant_filter_stats");
    if (statsEl) statsEl.textContent = "…";

    let result;
    try {
        result = await rpc("/website_sale/review/filter", {
            product_tmpl_id: tmplId,
            product_id: productId || null,
            variant_only: !!variantOnly,
        });
    } catch (e) {
        if (statsEl) statsEl.textContent = "";
        return;
    }
    if (!result?.ok) {
        if (statsEl) statsEl.textContent = "";
        return;
    }

    const allowed = new Set(result.message_ids || []);
    const messages = document.querySelectorAll(
        ".o-mail-Message, .o_portal_chatter_message, [data-message-id], .o_message"
    );
    messages.forEach((node) => {
        const mid =
            parseInt(node.getAttribute("data-message-id"), 10) ||
            parseInt(node.dataset?.messageId, 10) ||
            parseInt(node.dataset?.id, 10) ||
            null;
        if (!variantOnly) {
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

    if (statsEl && result.stats) {
        const s = result.stats;
        statsEl.textContent = s.count
            ? `(${s.count} review${s.count === 1 ? "" : "s"})`
            : "(no reviews for this variant)";
    }
}

function updateUrl(variantOnly, productId) {
    try {
        const u = new URL(window.location.href);
        if (variantOnly) {
            u.searchParams.set("wsre_variant_only", "1");
            if (productId) u.searchParams.set("product_id", String(productId));
        } else {
            u.searchParams.delete("wsre_variant_only");
        }
        window.history.replaceState({}, "", u.toString());
    } catch (_) {}
}

async function boot() {
    if (!hasReviewArea()) return;
    const tmplId = resolveTemplateId();
    if (!tmplId) return;

    const input = injectToggle();
    if (!input) return;

    input.addEventListener("change", async () => {
        const checked = !!input.checked;
        updateUrl(checked, resolveProductId());
        await applyFilter(checked);
    });

    // Re-filter when the customer changes combination
    document.addEventListener("change", (ev) => {
        if (
            ev.target?.matches?.(
                "input[name='product_id'], .js_variant_change, input.js_variant_change"
            )
        ) {
            if (input.checked) {
                applyFilter(true);
            }
        }
    });

    // Honour URL state on load
    const params = new URLSearchParams(window.location.search);
    if (params.get("wsre_variant_only") === "1" && resolveProductId()) {
        input.checked = true;
        await applyFilter(true);
    }
}

whenReady(() => {
    // Small delay so portal chatter DOM is present
    setTimeout(boot, 300);
});
