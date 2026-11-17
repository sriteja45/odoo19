# Phase 2 — Odoo 19 Native Mapping (KEEP / EXTEND / REMOVE)

**Module:** Customer Feedback, Ratings & Reviews  
**Target:** Odoo 19 Community  
**Implemented in:** `19.0.2.6.0`

## Goal

Map every customer-feedback feature to native Odoo 19 Community functionality and make the decision executable:

- **KEEP** — genuine business functionality not provided by native Odoo.
- **EXTEND** — native functionality is the source of truth and this module adds a business-specific projection/UI.
- **REMOVE** — duplicate native functionality must not be reintroduced.

The mapping was checked against Odoo 19's `rating.mixin` implementation. Odoo 19 computes `rating_avg` and `rating_count` from `rating.rating` rows using the native consumed/rating domain and exposes native repartition/statistics helpers.

## 1. Native rating source of truth

### Native Odoo — KEEP as source

`product.template` uses the native rating infrastructure supplied by Odoo's rating/website stack:

- `rating_avg`
- `rating_count`
- `rating_ids`
- `rating_get_stats()`
- `_rating_get_repartition()`

The module **must not create another product-level average/count source**.

### Module business layer — KEEP

`feedback.review` remains the business-review layer because native `rating.rating` does not provide:

- verified-purchase status
- invitation/token lifecycle
- moderation states
- review title
- customer-facing review workflow
- helpful/not-helpful review votes

Each approved `feedback.review` is linked to exactly one native `rating.rating` through `rating_id`.

## 2. Feature mapping

| Feature | Native Odoo 19 | Decision | Implementation |
|---|---|---|---|
| `feedback.request` | No delivery-triggered invitation/token workflow | **KEEP** | Custom model |
| Verified purchase | No native equivalent | **KEEP** | `feedback.review` + request/order/delivery relation |
| Review moderation | No native equivalent | **KEEP** | `pending/approved/rejected/hidden` |
| Review title | No native equivalent on `rating.rating` | **KEEP** | `feedback.review.review_title` |
| Review body/rating | Native `rating.rating` has rating/feedback | **EXTEND** | Business review is bridged to native row |
| Product average | Native `rating.mixin.rating_avg` | **REMOVE duplicate** | Native only |
| Product rating count | Native `rating.mixin.rating_count` | **REMOVE duplicate** | Native only |
| Product 1–5 histogram | Native on-demand repartition exists | **EXTEND** | Computed on demand via `_rating_get_repartition()`, no stored columns |
| Customer review totals | No equivalent aggregate for this workflow | **KEEP** | `res.partner` computed fields |
| Sale-order review completion | No equivalent | **KEEP** | Custom sale-order fields |
| Delivery-triggered invitation | No equivalent | **KEEP** | `stock.picking` integration |
| Waiting/expiry/reminder configuration | No equivalent | **KEEP** | `res.config.settings` |
| Dashboard | No equivalent for this workflow | **KEEP** | Custom dashboard |
| PDF/XLSX feedback report | No equivalent matching requirements | **KEEP** | Custom report/export |
| Resend invitation wizard | No equivalent | **KEEP** | Custom wizard |
| REST feedback API | No equivalent | **KEEP** | Custom API |
| Token review portal | No equivalent | **KEEP** | Custom website/portal controllers |
| Helpful/not-helpful votes | No equivalent for public review voting | **KEEP** | `feedback.review.vote` |
| Frontend rating display | Native rating infrastructure exists | **EXTEND** | Verified-review UI reads native average/count |
| `rating.rating` bridge | Native target | **KEEP** | `models/rating_bridge.py` |
| Explicit `rating` dependency | Native dependency | **KEEP** | Manifest declares it directly |

## 3. Duplicate-field removal contract

The following legacy product fields are intentionally absent:

- `product.template.average_rating`
- `product.template.total_reviews`
- `product.template.review_count`

Any future code attempting to add these fields is a Phase 2 regression.

API response keys such as `average_rating` and `review_count` are **external API contract names**, not duplicate ORM fields; they are populated from native `rating_avg` / `rating_count`.

## 4. Histogram decision

**Superseded in `19.0.2.9.0`.** Odoo 19 already provides on-demand rating repartition/statistics. The stored `rating_1_count` … `rating_5_count` columns and `last_review_date` described in the original Phase 2 plan (`19.0.2.6.0`) were removed by `migrations/19.0.2.9.0/pre-migrate.py`. `product.template.get_rating_distribution()` now calls native `_rating_get_repartition()` directly and `get_last_review_date()` runs a light search — neither is backed by a stored column.

No product-level histogram fields exist on `product.template`. Any future code reintroducing `rating_1_count` … `rating_5_count` (or an equivalent stored per-star count) as a `product.template` field is a Phase 2/Step 1 regression — it would recreate a second rating aggregate alongside native `rating_avg`/`rating_count`.

## 5. Native public submission boundary

The module disables the native free-form product review UI and sets `product.template._mail_post_access = 'write'`. It also guards `message_post()` so a non-internal caller cannot inject `rating_value` into a product message and create an unmoderated native rating.

This boundary is covered by `tests/test_rating_bridge.py` and remains a security requirement for Phase 7.

## 6. Executable verification

Static mapping check:

```bash
python3 tools/validate_step2_native_mapping.py
```

Odoo runtime checks:

```bash
./tools/validate_step1.sh
```

The Phase 2 regression suite is:

```text
tests/test_native_mapping.py
```

## 7. Completion status

**Phase 2 is implemented.** The KEEP / EXTEND / REMOVE decisions above are now represented in code and regression tests rather than remaining documentation-only decisions.

The next phase is **Phase 3 — Architecture Refactor**, whose focus is the review lifecycle and native-rating synchronization rather than re-mapping native features.
