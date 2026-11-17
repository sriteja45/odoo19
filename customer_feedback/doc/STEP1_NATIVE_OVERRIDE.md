# Step 1 — Native review vs custom verified-review path

**Version:** 19.0.2.18.0  
**Status:** Implemented / explicit architectural exception  
**Last updated:** 19.0.2.18.0 (hardening release)

---

## Official architectural exception (required reading)

> **Native Odoo's free-form product review submission does not enforce the
> required verified-purchase + post-delivery + moderation workflow.
> Therefore, the native public submission entry point is intentionally
> restricted, while the native `rating.rating` and `rating.mixin`
> infrastructure remains the source of truth for numeric scores, averages,
> counts, and star distribution.**

This is an **explicit, documented exception** to the general rule
“reuse / extend existing features”. It is **not** a silent disable of
native functionality. The exception is limited to the *public submission
entry point*; everything downstream (numeric rating storage, aggregates,
repartition) stays native.

---

## Decision

This module **extends the native** product-review experience on the eCommerce
site with a verified-purchase + moderated workflow. Native `rating.rating` /
`rating.mixin` remain the source of truth, and **Shared / Additive is the locked
default**.

The native Odoo free-form public submission entry point is restricted only
because it cannot enforce the required purchase, delivery, and moderation
eligibility rules. There is therefore exactly one public submission path for
verified reviews while preserving the native numeric rating infrastructure.

---

## Single submission path (required)

```
Customer
  ↓
Delivered Sale Order (stock.picking done)
  ↓
feedback.request  (token, expiry, invitation/reminder)
  ↓
Secure token URL  /feedback/review/<token>
  ↓
feedback.review   (status: pending | approved | rejected | hidden)
  ↓
Moderation (optional, configurable)
  ↓
rating.rating     (consumed=True only when approved)
  ↓
product.template.rating_avg / rating_count  (native aggregates)
```

No other public path may create a `rating.rating` (or a product review)
for `product.template`.

---

## What is disabled (and why)

| Native mechanism | How disabled | Why |
|------------------|--------------|-----|
| `website_sale.product_comment` view | Forced `active=False` in data + post-init | Hides free-form "Customer Reviews" form / portal.message_thread on product page |
| Safety xpath on `product_comment` | Template replace of `portal.message_thread` | If an editor re-activates the view, free-form form still does not appear |
| `product.template._mail_post_access` | Set to `'write'` (overrides website_sale `'read'`) | Public/portal users cannot post on product chatter |
| `product.template.message_post()` | Strips `rating_value` for non-internal, non-sudo callers | Defense-in-depth: even if ACL is bypassed, no unmoderated native rating is created |

---

## What remains native (source of truth)

- `rating.rating` numeric score and `consumed` flag
- `product.template.rating_avg` / `rating_count` (from `rating.mixin`)
- `_rating_get_repartition()` for star distribution
- Schema.org aggregateRating when ratings exist

---

## What this module adds (only what native lacks)

- Post-delivery invitation + secure token (no login required)
- Verified-purchase flag/badge
- Moderation workflow
- Review title + body (business text lives only on `feedback.review`)
- Helpful / Not helpful voting
- Sort/filter on product page
- Portal "My Reviews", dashboard, reports, REST API

---

## Hardening rules (19.0.2.18.0)

- Public review listing is bounded (default 20, maximum 100) and uses
  `limit`/`offset`; the product page exposes Load More rather than loading an
  unbounded review set.
- Deleting a business review normally de-consumes its linked native
  `rating.rating` row and preserves native rating history. Physical deletion is
  an explicit internal purge operation only.
- Token validation returns only the minimum public payload required by the
  review client: status, product, expiry and submission state.
- Review cards surface the purchased variant attributes when available.

## Explicit non-goals

- Do **not** re-enable native free-form product reviews while this module is
  installed and owns the experience.
- Do **not** introduce a second stored average/count field on
  `product.template` or `feedback.review`.
- Do **not** copy review body into `rating.rating.feedback` (text ownership
  stays on `feedback.review`).

---

## Enforcement points in code

1. `views/website_templates.xml` — deactivate `website_sale.product_comment`,
   inject verified list + compact native stars, safety xpath.
2. `models/product_template.py` — `_mail_post_access = 'write'`,
   `message_post()` rating_value guard.
3. `models/rating_bridge.py` — only bridge creates/updates product
   `rating.rating` rows linked via `feedback_review_id`.
4. `controllers/feedback_portal.py` — sole public submit/edit endpoints
   (token-gated).
5. `__init__.py` `post_init_hook` — re-assert `product_comment` inactive +
   bridge approved reviews.
6. Tests: `tests/test_rating_bridge.py` (test_06, test_07),
   `tests/test_step1_native_override.py`.

---

## Native-rating ownership contract

See also: `doc/OWNERSHIP_DECISION.md` (formal decision record).

Default mode is **shared** (additive), stored in
`ir.config_parameter` key `customer_feedback.rating_ownership`.
Missing or invalid values fall back to `shared`.

```python
# models/rating_bridge.py
def _get_rating_ownership(self):
    # returns 'shared' (default) or 'exclusive'
```

Under **shared** (default):

- approved linked reviews contribute via bridged `rating.rating` rows;
- existing/unowned native product ratings remain `consumed=True` and count;
- deactivation of unowned ratings is a no-op;
- historical `consumed=False` rows are never mass-reactivated.

Under **exclusive** (explicit opt-in only):

- only ratings linked to approved `feedback.review` may remain consumed for
  `product.template`;
- unowned product ratings are set `consumed=False` (preserved, not deleted);
- requires explicit business approval (see OWNERSHIP_DECISION.md).

Linked review lifecycle is unchanged in both modes: approved → consumed=True;
pending/rejected/hidden → consumed=False. Ratings on other `res_model` values
are never modified.

---

## If the product requirement changes

If the business later wants only "simple rating + review" without verified
purchase or moderation, remove this module's ownership of the path:

1. Stop deactivating `website_sale.product_comment`.
2. Restore `_mail_post_access` to website_sale behaviour (or remove override).
3. Remove the `message_post` rating_value strip.
4. Prefer native portal reviews; keep optional bridge only if needed.
5. Change `RATING_OWNERSHIP` away from `'exclusive'` (see OWNERSHIP_DECISION.md).

Until that decision, the architecture above is mandatory.
