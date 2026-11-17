# Phase 1 — Full Module Audit
### Module: `customer_feedback` — Customer Feedback, Ratings & Reviews (Odoo 19 Community)
### Manifest version at time of audit: `19.0.2.1.0`

This is a pure **inventory/fact-finding** pass (per the 10‑phase plan). It records what exists,
how it's wired together, and flags things Phase 2 (Native Mapping / KEEP‑EXTEND‑REMOVE) will need
to decide on. No code was changed in this pass.

---

## 0. Headline finding

This is **not a greenfield module**. The CHANGELOG, migration script, and code comments show it has
already been through a prior architecture refactor ("Option B bridge", version `19.0.2.0.0`) that
moved toward exactly the target architecture described in the 10‑phase plan: `rating.rating` as the
native source of truth, `feedback.review` as an extended business layer. Phase 2 needs to verify how
much of the plan is *already done* vs. still open, rather than assuming a from‑scratch refactor.

---

## 1. Manifest & Dependencies

| Field | Value |
|---|---|
| `name` | Customer Feedback, Ratings & Reviews |
| `version` | 19.0.2.1.0 |
| `category` | Sales/Sales |
| `license` | LGPL-3 |
| `application` | True |
| `post_init_hook` | `post_init_hook` → bridges pre-existing approved reviews to `rating.rating` |
| `external_dependencies.python` | `xlsxwriter` (optional; required only when Excel export is used) |

**`depends`:** `base_setup`, `sale_management`, `stock`, `mail`, `portal`, `website`, `website_sale`, `rating`
— all Community modules, no Enterprise dependency detected in the manifest.

---

## 2. Models Inventory

| Model (`_name`/`_inherit`) | File | Type | Purpose |
|---|---|---|---|
| `feedback.request` | `models/feedback_request.py` | Model | Verified-purchase invitation record: token, waiting/expiry windows, email status/retry tracking, links to sale order line + picking |
| `feedback.review` | `models/feedback_review.py` | Model | The customer's actual review: rating, title, text, moderation status, votes |
| `feedback.review` (extended) | `models/rating_bridge.py` | Inherit | Adds `rating_id` (M2O `rating.rating`) + sync/unlink/bridge logic — **this is the Option B bridge** |
| `feedback.review.vote` | `models/feedback_review_vote.py` | Model | One helpful/not-helpful vote per visitor per review |
| `feedback.dashboard` | `models/feedback_dashboard.py` | TransientModel | Aggregated KPIs for the backend dashboard |
| `feedback.report.wizard` | `models/feedback_report_wizard.py` | TransientModel | PDF + 6-sheet Excel export |
| `feedback.resend.email.wizard` | `models/feedback_resend_email_wizard.py` | TransientModel | Bulk resend invitation/reminder, with retry-counter reset |
| `product.template` (extended) | `models/product_template.py` | Inherit | Legacy `average_rating`/`total_reviews`/`review_count` + genuine extra 1★–5★ distribution counts + `last_review_date` |
| `res.partner` (extended) | `models/res_partner.py` | Inherit | `total_reviews`, `average_rating_given`, `last_review_date` — batched via `_read_group` |
| `sale.order` (extended) | `models/sale_order.py` | Inherit | Feedback stats + `review_completion_status` (none/partial/complete) |
| `stock.picking` (extended) | `models/stock_picking.py` | Inherit | Hooks `button_validate()` to auto-create feedback requests on outgoing delivery |
| `res.config.settings` (extended) | `models/res_config_settings.py` | Inherit | Manual get/set for int + boolean config params (documented workaround for an Odoo `set_values()` quirk with `0`/`False`) |
| `report.customer_feedback.report_product_ratings_document` | `report/feedback_report.py` | AbstractModel | QWeb data provider for the PDF report |

### 2.1 Key constraints found (Model / DB level)
- `feedback.request`: unique `token`; unique `sale_order_line_id` (**one request per order line**)
- `feedback.review`: `CHECK(rating BETWEEN 1 AND 5)`; unique `request_id` (**one review per request**)
- `feedback.review.vote`: unique `(review_id, voter_key)` (**one vote per visitor per review**)

### 2.2 Native-rating bridge logic (`rating_bridge.py`) — as currently implemented
- `_sync_native_rating()`: on `status == 'approved'` → create/update linked `rating.rating` with `consumed=True`; otherwise keep the row but set `consumed=False` (excluded from native averages, kept for audit trail).
- `_unlink_native_rating()`: de-consumes the linked `rating.rating` row(s) on normal review unlink; physical deletion is reserved for explicit internal purge.
- `_bridge_all_approved_to_native_rating()`: idempotent batch bridge, called from both `post_init_hook` and the `19.0.2.0.0` post-migrate script.
- Uses `self.env.context.get('skip_rating_bridge')` to avoid recursive writes when the bridge itself sets `rating_id`.

### 2.3 Legacy/duplicate fields still present on `product.template`
`average_rating`, `total_reviews`, `review_count` are explicitly commented **"Legacy field. Prefer native rating_avg/rating_count"** and are kept only for backward-compatible reports/views. They are computed by `_recompute_rating_stats()`, which explicitly does **not** touch `rating_avg`/`rating_count` (native fields owned by `rating.mixin`). → **Flag for Phase 2/4**: decide whether these can now be fully removed or must stay (they're still referenced in 8+ view/report locations, see §7).

---

## 3. Controllers Inventory

| File | Route | Method | `auth` | `csrf` | Purpose |
|---|---|---|---|---|---|
| `controllers/api_controller.py` | `/api/feedback/request` | POST | `user` | `False` | Create a feedback request (API 1) |
| " | `/api/feedback/token/<token>` | GET | `public` | `False` | Validate a token (API 2) |
| " | `/api/feedback/review` | POST | `public` | `False` | Submit a review via API (API 3) |
| " | `/api/products/<id>/reviews` | GET | `public` | `False` | Public product reviews + distribution (API 4) |
| " | `/api/customer/reviews` | GET | `user` | `False` | Logged-in customer's own reviews (API 5) |
| `controllers/feedback_portal.py` | `/feedback/review/<token>` | GET | `public`, `website=True` | n/a | Token review form |
| " | `/feedback/review/<token>/submit` | POST | `public`, `website=True` | `True` | Submit review from portal form |
| " | `/feedback/review/<token>/edit` | GET/POST | `public`, `website=True` | GET n/a / POST `True` | Edit existing review (gated by `allow_review_edit` setting) |
| " | `/feedback/product/<id>/reviews` | GET | `public`, `website=True` | `False` | AJAX fragment: sorted/filtered review list |
| " | `/feedback/review/<id>/vote` | POST | `public`, `website=True` | `False` | Cast/change/retract helpful vote |
| " | `/my/reviews` | GET | `user`, `website=True` | n/a | Portal "My Reviews" page |

**Flag for Phase 7 (Security & API):** all `type='http'` JSON API routes (`/api/feedback/*`) run with `csrf=False`, and three of them (`token` validate, `submit_review`, vote) are `auth='public'`. This is expected for a public, no-login review flow secured by opaque token, but it needs explicit rate-limiting / abuse review in Phase 7 (nothing throttles repeated token-guessing or repeated vote/submit calls today beyond the DB-level unique constraints).

---

## 4. Security Inventory

**Groups** (`security/feedback_security.xml`): `group_feedback_user` (read-only) → `group_feedback_moderator` (implies user; can approve/reject/hide/restore, no create/unlink) → `group_feedback_manager` (implies moderator; full CRUD). One `ir.module.category` + `res.groups.privilege`.

**Record rules:**
| Rule | Model | Groups | Domain |
|---|---|---|---|
| `feedback_review_rule_manager` | feedback.review | manager | `[(1,'=',1)]` (all) |
| `feedback_review_rule_moderator` | feedback.review | moderator | all, no create/unlink |
| `feedback_request_rule_moderator` | feedback.request | moderator | all, read-only |
| `feedback_review_rule_user` | feedback.review | user | approved OR own |
| `feedback_review_rule_portal` | feedback.review | portal | own only, read-only |

**ACL (`ir.model.access.csv`, 16 rows)** covers `feedback.request`, `feedback.review`, `feedback.review.vote`, `feedback.report.wizard`, `feedback.resend.email.wizard` for manager/moderator/user/sales-salesman/portal/public groups. `base.group_public` explicitly has **all perms = 0** on `feedback.review` (public access is only through the `sudo()`-using controllers, by design).

**Flag for Phase 7:** No `ir.model.access.csv` row for `feedback.review.vote` for `base.group_public`/portal — voting works only because the controller uses `sudo()`. Worth confirming this is intentional and that no other entry point could touch votes without the sudo controller.

---

## 5. Automation, Data & Mail

| Artifact | File | Detail |
|---|---|---|
| Cron 1 | `data/ir_cron.xml` | `ir_cron_process_feedback_requests` — hourly, calls `_cron_process_feedback_requests()` (sends invitations past waiting period, expires stale requests) |
| Cron 2 | " | `ir_cron_send_feedback_reminders` — every 6h, calls `_cron_send_reminders()` |
| Sequence | `data/ir_sequence.xml` | `FB`-prefixed, 5-digit padding, for `feedback.request` |
| Export template | `data/ir_exports.xml` | `feedback.review` export preset (product, customer, rating, title, text, status, date) |
| Mail templates (3) | `data/mail_templates.xml` | Invitation, Reminder (both on `feedback.request`), Thank-you (on `feedback.review`) — all `auto_delete=True`, inline HTML, token link embedded via `object.get_base_url()` |

**Retry/failure handling:** `_send_templated_email()` is a shared helper (used by both cron paths and the resend wizard) that tracks `pending/sent/failed/retried` + a retry counter per email type, capped by `customer_feedback.max_email_retries` (default 3), and creates an internal `mail.mail` notice to the configured admin/company email once retries are exhausted.

---

## 6. Frontend / Website Integration

| File | Role |
|---|---|
| `static/src/interactions/feedback_review_vote.js` | Odoo 19 `Interaction` (not legacy `publicWidget`) handling helpful/not-helpful clicks via `fetch()` |
| `views/website_templates.xml` | Deactivates `website_sale.product_comment` (native free-form review thread) to prevent a second, unmoderated submission path; injects a compact star widget under the product title that reads **native** `rating_avg`/`rating_count` only; injects the verified-review section after the product description; adds a safety-net override in case an editor re-activates the native comment view |
| `views/snippets/s_feedback_reviews.xml` | The actual review list snippet + `product_reviews_list` fragment template (used by both the full page and the AJAX sort/filter endpoint) |
| `views/portal_templates.xml` (258 lines) | 7 QWeb templates: review form, already-submitted, expired, invalid-token, edit-disabled, edit-form, "My Reviews" |

**Observation:** the "single coherent review experience" goal from the plan (no duplicate submission paths between native portal reviews and this module) already has explicit code and comments addressing it (§ `hide_native_message_thread` template). Phase 2/6 should verify this holds on a real Odoo 19 install (native view names/structure can drift between point releases) — flagged as PENDING in the module's own `doc/ACCEPTANCE_TESTS.md`.

---

## 7. Views, Actions, Menus, Reports (full XML id inventory)

| File | Records/Templates defined |
|---|---|
| `feedback_dashboard.xml` | `view_feedback_dashboard_form`, `action_feedback_dashboard` |
| `feedback_menus.xml` | 11 menu items (Feedback root → Dashboard / Reviews / Moderation / Requests / Reports submenu with 4 report links + export wizard) |
| `feedback_report_views.xml` | Top/lowest-rated product lists, monthly review report (list+pivot), product ratings report action |
| `feedback_report_wizard_views.xml` | Wizard form + action |
| `feedback_request_views.xml` | list, form, search, action for `feedback.request` |
| `feedback_resend_email_wizard_views.xml` | wizard form + action |
| `feedback_review_graph.xml` | 4 graph views (overall, by month, distribution, by customer) |
| `feedback_review_pivot.xml` | 2 pivot views |
| `feedback_review_views.xml` | list, form, search, 4 actions (incl. moderation-specific action) |
| `portal_templates.xml` | 7 portal QWeb templates (see §6) |
| `product_template_views.xml` | Feedback tab on Product Template form — shows **both** legacy (`average_rating`, `total_reviews`) and native (`rating_avg`, `rating_count`, explicitly labelled "(native)") fields side by side |
| `res_config_settings_views.xml` | Settings panel form (waiting/expiry/reminder days, retries, moderation toggle, name-display mode, edit toggle, min/max review length) |
| `sale_order_views.xml` | Feedback stat button on Sale Order form |
| `website_templates.xml` | See §6 |
| `snippets/s_feedback_reviews.xml` | See §6 |
| `report/feedback_report.xml` | `action_report_product_ratings` + `report_product_ratings_document` QWeb report |

**Reports:** one PDF report (product ratings, with recent-reviews-per-product, date-range filterable) and one 6-sheet Excel workbook (Rating by Product, Reviews by Month, Customer Satisfaction, Rating Distribution, Most/Least Reviewed, Pending Moderation) via `feedback.report.wizard` — uses the optional external `xlsxwriter` package only when Excel export is requested; the module remains installable without it.

---

## 8. Tests Inventory (9 files, all present, all `TransactionCase`/`HttpCase` + `@tagged('post_install','-at_install')` except vote tests)

| File | Lines | Covers |
|---|---|---|
| `tests/common.py` | 55 | Shared fixture: confirmed & delivered sale order |
| `test_feedback_request.py` | 114 | Request creation on delivery, token uniqueness, expiry/reminder cron logic |
| `test_feedback_review.py` | 154 | Review creation, moderation states, rating constraints, name/edit logic |
| `test_api_controller.py` | 93 | `HttpCase` end-to-end tests against `/api/feedback/*` |
| `test_product_rating.py` | 52 | Average recompute on approval |
| `test_product_reviews_sort.py` | 98 | `HttpCase` tests of `/feedback/product/<id>/reviews` sort/filter fragment |
| `test_mail_templates.py` | 63 | Renders all 3 templates via `generate_email()` (no SMTP) |
| `test_review_votes.py` | 61 | Vote add/change/retract + counter sync |
| `test_resend_email_wizard.py` | 70 | Wizard resend behaviour |
| `test_report_wizard.py` | 55 | PDF/XLSX export |

**Gaps flagged for Phase 10:** no dedicated test file for the **rating bridge** itself (`rating_bridge.py` / `_sync_native_rating`, `_bridge_all_approved_to_native_rating`) or for the **migration script**, despite these being the core of the recent architecture refactor and the subject of the module's own `doc/run_audit.py` orphan/duplicate-checker. This is the most important testing gap to close before Phase 10 sign-off.

---

## 9. Migrations, Tools & Docs (non-code but relevant to "production-level" claim)

| File | Purpose |
|---|---|
| `migrations/19.0.2.0.0/post-migrate.py` | Idempotent bridge of pre-existing approved reviews to `rating.rating` on upgrade |
| `doc/run_audit.py` | Standalone `odoo-bin shell` script to detect orphaned/duplicate native ratings post-deploy |
| `doc/ACCEPTANCE_TESTS.md` | 18-row manual acceptance matrix; **most rows are marked `PENDING (staging)`**, only 3 are `PASS (code review)` |
| `doc/STAGING_VALIDATION.md` | Step-by-step staging validation guide (fresh install, upgrade-from-19.0.1.8.0, native-rating checks) |
| `tools/perf_load_test.py` | Load-test generator matching the plan's stated 10k requests / 50k reviews scale target — **not part of the automated test suite**, must be run manually against disposable staging |
| `CHANGELOG.md` | Documents the prior `19.0.2.0.0` architecture refactor explicitly |

**Flag for Phase 9/10:** the module's own documentation is honest that the architecture work is *code-reviewed* but **not yet verified on a live Odoo 19 Community database** — no install/upgrade/duplicate-rating/performance test has actually been executed per these docs. This is the single most important item Phase 10 must close before anything can be called production-ready, and it's already been explicitly flagged by whoever wrote these docs.

---

## 10. Summary Table — Inventory Counts

| Category | Count |
|---|---|
| Models (new) | 7 (`feedback.request`, `feedback.review`, `feedback.review.vote`, `feedback.dashboard`, `feedback.report.wizard`, `feedback.resend.email.wizard`, report abstract model) |
| Models extended (`_inherit`) | 5 (`product.template`, `res.partner`, `sale.order`, `stock.picking`, `res.config.settings`) + `feedback.review` self-extension for the bridge |
| Controllers / routes | 11 (5 REST API + 6 portal/website) |
| Security groups | 3 |
| Record rules | 5 |
| ACL rows | 16 |
| Cron jobs | 2 |
| Mail templates | 3 |
| Views/actions/menus (XML records) | ~45 |
| QWeb portal/website templates | 11 |
| Reports | 1 PDF + 1 multi-sheet XLSX |
| Test files | 9 (covering all major flows except the rating bridge itself) |
| Total module LOC (excl. `__pycache__`, icon) | ≈ 3,540 lines |

---

## 11. Items carried forward to Phase 2 (Native Mapping / KEEP-EXTEND-REMOVE)

1. **Legacy duplicate fields** on `product.template` (`average_rating`, `total_reviews`, `review_count`) — still wired into 8+ views/reports; decide removal vs. permanent legacy status.
2. **`xlsxwriter` optional dependency** — install it only on servers where Excel export is required; the core module does not require it for installation or normal operation.
3. **Missing ACL row** for `feedback.review.vote` under portal/public groups — confirm sudo-only access is the intended final design.
4. **CSRF-disabled, public-auth API routes** — confirm intended for Phase 7, and decide if rate-limiting/abuse controls are needed.
5. **No automated test coverage of the rating bridge or migration script** — the newest and most architecturally important code has the weakest test coverage; prioritize for Phase 10.
6. **All staging/upgrade/duplicate-rating/performance verification is still `PENDING`** per the module's own docs — this governs the Phase 10 sign-off criteria and should be scheduled early, since Phases 3–9 may otherwise build on an unverified foundation.

---

*End of Phase 1 audit. Ready to proceed to Phase 2 (Odoo 19 Native Mapping: KEEP / EXTEND / REMOVE decision per feature) on request.*
