## 19.0.2.30.0 — Steps 1–3: More editable Website Builder structure

- **Step 1** — Removed outer `o_not_editable` wrapper around the toolbar so the toolbar area becomes selectable in the Website Builder.
- **Step 2** — Title block is now an explicit `o_editable` zone. Nested structure clearer (title / toolbar wrap / list).
- **Step 3** — Added secondary OWL option component for the title block for easier selection and styling.
- List container (`#o_feedback_reviews_list_container`) remains `o_not_editable` to protect AJAX sort/filter/load-more.
- CSS editor affordances improved for the new title block and toolbar wrap.
- **No functional change** to votes, sort/filter, load-more, moderation, rating bridge, token flow, portal, or Settings auto-injection.

## 19.0.2.29.0 — Step 7: Website Builder polish

- Section title remains freely editable in the Website Builder.
- Toolbar and review list marked `o_not_editable` so AJAX/JS structure is not broken while editing.
- Clearer editor placeholder text; dashed “Hidden on frontend” hint when per-page hide is on.
- CSS editor affordances only (no runtime behaviour change).
- **No functional change** to votes, sort/filter, load-more, moderation, rating bridge, token flow, portal, or Settings auto-injection.

## 19.0.2.28.0 — Steps 4–6: complete builder options wiring

- **Step 4** — All Customize actions wired to existing CSS classes (visibility, title size/color, card layout, filter/load-more styles).
- **Step 5** — Special cases:
  - Default sort via `data-default-sort` (read by existing frontend Interaction on load).
  - Text align (left/center/right) + top/bottom spacing class options.
  - Hide entire block still keeps faint outline in editor.
- **Step 6** — Tests & docs updated (`STEP4_5_6_OWL_BUILDER_OPTIONS.md`).
- **No functional change** to votes, sort/filter AJAX, load-more, moderation, rating bridge, token flow, or portal.

## 19.0.2.27.0 — Restore Website Builder Customize options (OWL)

- **Steps 1–3 (Odoo 19 OWL builder):**
  - Added `FeedbackReviewsOption` OWL component + `FeedbackReviewsOptionPlugin`.
  - Options panel restored for `.s_feedback_reviews` (visibility toggles, title size/color, card layout, filter/load-more styles).
  - Registered under `website.website_builder_assets`.
- Uses only existing CSS class hooks (`.o_feedback_hide_*`, layouts, etc.).
- **No functional change** to votes, sort/filter, load-more, moderation, rating bridge, token flow, portal, or auto-injection.

## 19.0.2.26.0 — Fix Odoo 19 upgrade: remove website.snippet_options inherit

- **Fix:** `External ID not found: website.snippet_options` on upgrade/install.
- Odoo 19 no longer provides the legacy `website.snippet_options` QWeb template (`we-checkbox` / `we-select` panel). Snippet options are OWL builder plugins.
- Removed `s_feedback_reviews_options` inherit so the module installs cleanly.
- **Unchanged:** product reviews UI, votes, sort/filter, load-more, moderation, rating bridge, token flow, portal, CSS class hooks (`.o_feedback_hide_*`, layouts, etc.), snippet registration in Website Builder blocks panel, Settings auto-injection toggle.
- Builder Customize panel class toggles from the old we-* system are not available until reimplemented as Odoo 19 OWL options (optional follow-up).

## 19.0.2.25.0 — Steps 7–8: Settings polish, per-page hide, regression tests

- **Step 7**
  - Clearer Settings help for *Show Reviews on Product Pages* (global ON/OFF + manual snippet).
  - Snippet option **Hide entire block on frontend** (`o_feedback_hide_block`) for per-page hide.
  - In Website Editor the hidden block stays faintly visible/selectable (no accidental loss).
  - Section attribute `data-feedback-reviews="1"` for optional theming hooks.
  - Injection template comments updated; behaviour of auto-injection unchanged.
- **Step 8**
  - `tests/test_web_builder_options.py`: snippet/options/JS-critical class regression.
  - `doc/STEP7_8_WEB_BUILDER.md` + manual checklist.
- **No functional change** to votes, sort/filter, load-more, moderation, rating bridge, token flow, or portal.

## 19.0.2.24.0 — Steps 4–6: Richer builder styles, dynamic safety, editor placeholder

- **Step 4 — Richer Customize options** (CSS class based, default = previous look):
  - Title size: Small / Medium / Large
  - Title color: Default / Primary / Muted
  - Card layout: Default / Compact / Bordered cards
  - Filter button style: Outline / Soft fill
  - Load more button: Outline primary / Solid primary / Link style
- **Step 5 — Dynamic content safety**
  - All visibility & style classes live on `.s_feedback_reviews` section ancestor
  - AJAX sort/filter/load-more refreshed cards continue to respect builder options
  - No controller or JS API changes
- **Step 6 — Editor affordances**
  - When block has no product context (CMS page / builder drop): dashed placeholder + sample skeleton cards
  - Option to hide sample cards
  - Clear hint text that real reviews appear on product pages
- Product-page auto-injection setting (Settings → Show Reviews on Product Pages) unchanged.
- **No functional change** to votes, moderation, rating bridge, token flow, portal, or AJAX endpoints.

## 19.0.2.23.0 — Steps 1–3: Stronger web-builder structure & expanded options

- **Step 1** — Section is explicitly builder-aware (`o_editable`, clear selection).
- **Step 2** — Clear nested structure inside the snippet:
  - `.o_feedback_title_block` (title)
  - `.o_feedback_reviews_toolbar` (sort/filter)
  - `.o_feedback_list_block` / `#o_feedback_reviews_list_container` (AJAX list)
  - Card-level classes: `.o_feedback_card_stars`, `.o_feedback_card_title`, `.o_feedback_card_meta`, `.o_feedback_card_variant`
- **Step 3** — Expanded Customize options (all default OFF = previous behaviour):
  - Hide review title / author & date / purchased variant / star rating on cards
  - Card layout: Default | Compact
  - Existing hides (title, toolbar, media, verified, votes) + spacing + align + default sort retained
- CSS rules for new hide classes and compact layout live on the section ancestor so AJAX-refreshed cards still respect them.
- **No functional change**: votes, sort/filter, load-more, moderation, rating bridge, token flow, portal unchanged.

## 19.0.2.22.0 — Step 7: Website Builder validation & settings tests

- Added `doc/STEP7_WEB_BUILDER_VALIDATION.md` acceptance checklist (builder options, product-page toggle, regression).
- Added `tests/test_web_builder_settings.py` for `feedback_show_on_product_page` default and get/set round-trip.
- No functional changes to reviews, moderation, votes, rating bridge, or portal.

## 19.0.2.21.0 — Website Builder style, product-page toggle, default sort (Steps 4–6)

- **Step 4 — Style options** in Website Builder Customize panel for the reviews block:
  - Text align (default / center / right)
  - Top spacing (none / small / medium / large / XL)
  - Bottom spacing (same)
- **Step 5 — Product-page auto-injection toggle**
  - New setting: *Show Reviews on Product Pages* (Settings → Customer Feedback → Website Display)
  - Default **True** (unchanged behaviour)
  - When False, product pages no longer auto-inject the reviews section; the snippet can still be dropped manually in the Website Builder
- **Step 6 — Default sort option**
  - Website Builder option sets `data-default-sort` on the section
  - Frontend Interaction applies it once on load (and refreshes list if not newest)
- No changes to moderation, voting, rating bridge, controllers, or models beyond the new config flag.

## 19.0.2.20.0 — Website Builder snippet options (Steps 1–3)

- Snippet options for the Customer Reviews block in Website Builder Customize panel:
  - Hide section title
  - Hide sort & filter bar
  - Hide review photos & videos
  - Hide verified purchase badge
  - Hide helpful votes
- Options use `data-select-class` on `.s_feedback_reviews` (persisted in page DOM).
- Visibility enforced by CSS only; default (no classes) keeps current UI.
- No changes to controllers, models, moderation, voting, AJAX sort/filter, or rating bridge.

## 19.0.2.19.0 — Step 8: Review photos & videos

- New model `feedback.review.media` with image/video type, sequence, and moderation status.
- Storage via standard `ir.attachment` (filestore by default; S3/object storage when configured on the instance).
- Portal review form: multipart upload widget for photos & videos with server-side type/size/count validation.
- Config settings: enable media, max images/videos, max file size, optional separate media moderation.
- Moderation gate: media follows review status by default; optional per-media approve/reject.
- Product-page review cards render approved images (thumbnails) and videos.
- Backend review form lists media with Approve/Reject actions; list view shows media count.

## 19.0.2.18.0

- **Hardening — bounded review retrieval:** product-page review rendering and the
  `/feedback/product/<id>/reviews` endpoint now use a shared bounded query helper
  with `limit`/`offset` pagination (default 20, max 100) and a Load More UI.
- **Hardening — native rating lifecycle:** deleting a `feedback.review` now
  de-consumes its linked `rating.rating` instead of physically deleting native
  rating history. Permanent deletion is reserved for an explicit internal purge.
- **Hardening — token API privacy:** `/api/feedback/token/<token>` no longer
  returns the customer's name and explicitly reports `already_submitted`.
- **Hardening — customer review API:** `/api/customer/reviews` now supports
  bounded pagination and stable ordering.
- **UX — purchased variant:** approved review cards display the purchased
  product variant attributes when available.
- **Architecture/docs:** standardized wording to “extend native + verified
  workflow”; Shared/Additive remains the default and Exclusive remains an
  explicit admin/migration-only exception.
- **Packaging:** `xlsxwriter` is now an optional runtime dependency; Excel export
  already reports a clear actionable error when the package is unavailable.

## 19.0.2.17.2

- **Fix RPC error on product form:** `action_view_reviews` was only on
  `product.template`. Opening the product as `product.product` (variant form)
  raised `AttributeError`. Added a thin delegate on `product.product`.

## 19.0.2.17.1

- **UI — product page: single rating block, no native accordion:**
  - Remove native `o_product_page_reviews_link` stars from `website_sale.product_title`
    so only `o_feedback_rating_compact` remains under the product name.
  - Replace entire `o_shop_discussion_rating` / `#o_product_page_reviews` shell
    from `website_sale.product_comment` (not only `message_thread`), so the
    native "Customer Reviews" accordion never appears even if the view is
    re-activated.
  - Shared ownership aggregates unchanged (native `rating_avg` / `rating_count`).

## 19.0.2.17.0

- **Architecture — Option B Shared / Additive ownership (locked default):**
  - Default product-rating ownership is now **shared**: existing native
    `rating.rating` rows continue to contribute to `rating_avg` /
    `rating_count` alongside approved verified reviews.
  - Runtime mode stored in `ir.config_parameter`
    (`customer_feedback.rating_ownership`); missing/invalid → `shared`.
  - `_deactivate_unowned_product_ratings()` is a no-op under shared; exclusive
    deactivation is an explicit opt-in only.
  - No mass reactivation of historical `consumed=False` rows.
  - Settings UI: Product Rating Ownership (shared / exclusive) with clear
    warning that exclusive changes existing Odoo rating behaviour.
  - Tests updated for shared default, coexistence, exclusive opt-in, and
    no historical reactivation.
  - Docs: `doc/OWNERSHIP_DECISION.md` rewritten for shared default.

## 19.0.2.16.1

- **Critical fix — rating always saved as 0:** `feedback.review.create()`
  popped the numeric `rating` from vals (related field) but called
  `_sync_native_rating()` *without* passing that value. The bridge then
  read the still-empty related field, skipped native row creation, and the
  UI showed `0.0 / 5`, empty stars, and "No ratings yet" on the product page
  even after a valid 1–5 star submit. Create now captures scores and passes
  them explicitly: `_sync_native_rating(rating_value=...)`.

## 19.0.2.16.0

- **STEP 5 — Automated tests:** `tests/test_step5_mail_send.py` covers force_send
  invitation path and FK-safe `invitation_mail_id` handling after Odoo auto-deletes
  sent `mail.mail` rows.
- **STEP 6 — Phase 9 Performance & Edge Cases:**
  - New `doc/PHASE9_PERFORMANCE_EDGE_CASES.md` (edge matrix, perf posture, bulk script)
  - New `tests/test_step6_edge_cases.py` (rating bounds, text length, one-review-per-request,
    reject/consumed, float→star int, reconcile idempotency)
  - Existing `tools/perf_load_test.py` documented as staging-only load generator
- **STEP 7 — Production verification package:**
  - `doc/STEP7_ODOO19_VALIDATION.md` updated (module version, automated test section, sign-off table)
  - `doc/README.md` Phase 9/10 status updated
  - New static guard `tools/validate_step5_6_7.py`

## 19.0.2.15.5

- **Fix FK crash on force_send invitation/reminder:** After successful SMTP
  send, Odoo auto-deletes the `mail.mail` row. Writing that id into
  `invitation_mail_id` / `reminder_mail_id` violated the foreign key and
  rolled back the status update (logs: `feedback_request_invitation_mail_id_fkey`).
  Now the FK is stored only when the `mail.mail` row still exists; a deleted
  post-send row is treated as successful delivery (`status=sent`).

## 19.0.2.15.4

- **Fix 500 on product page:** QWeb `TypeError: can't multiply sequence by non-int of type 'float'`
  when rendering review stars. `feedback.review.rating` is a Float (related to
  `rating.rating`); string multiplication now uses `int(round(...))`.
  - `views/snippets/s_feedback_reviews.xml` (`product_reviews_list`)
  - `views/portal_templates.xml` (My Reviews table)
  - `data/mail_templates.xml` (thank-you email stars)
- **Manual invitation/reminder send:** UI actions (`action_send_invitation`,
  `action_send_reminder`) now use `force_send=True` so SMTP is attempted
  immediately instead of leaving mails stuck in Outgoing until the mail queue
  cron runs. Cron/bulk path still uses `force_send=False` (queue).
- Status tracking improved: after force_send, `invitation_email_status` /
  `reminder_email_status` reflect actual `mail.mail.state` (sent / queued / failed).

## 19.0.2.15.3

- P0 STEP 2 — Native review override documentation hardened:
  - `doc/STEP1_NATIVE_OVERRIDE.md` now contains the official architectural
    exception statement explaining why the native free-form submission path
    is restricted while native rating.rating / rating.mixin remain the
    source of truth.
  - Version header and cross-links updated.
- P0 STEP 3 — Exclusive rating ownership formalised:
  - New `doc/OWNERSHIP_DECISION.md` decision record with business/lead
    sign-off table, rationale, exit path, and explicit YES/NO ownership
    statement.
  - `doc/STEP2_RATING_CONSISTENCY.md` points to the decision record.
  - `models/rating_bridge.py` module docstring links to both decision docs.
- No functional/runtime behaviour change. Documentation and policy clarity only.

## 19.0.2.15.2

- P0 tooling fix: removed exact version pins from static validators so they accept the current 19.0.2.15.x series (and future patches) instead of failing on every bump.
  - `tools/validate_step2_step3.py` — baseline-style check (≥ 19.0.2.15.0)
  - `tools/validate_step6_step7.py` — baseline-style check (≥ 19.0.2.13.0)
- P0 tooling fix: `tools/step1_runtime_audit.py`
  - Corrected expected vote field name (`vote` instead of stale `vote_type`)
  - Added clear guard when the script is executed outside `odoo-bin shell` (prevents `NameError: env`)

## 19.0.2.15.1

- Step 1: made product-rating ownership explicit and exclusive in the native rating bridge.
- Renamed the enforcement implementation to `_deactivate_unowned_product_ratings()` with a compatibility alias.
- Reconciliation now documents and enforces that only module-owned approved product ratings contribute to native aggregates; unrelated-model ratings are untouched.

## 19.0.2.15.0 — Steps 2-3: native rating consistency + acceptance package

### Step 2 — Native aggregates must match approved verified reviews

Problem: `product.template.rating_avg` / `rating_count` include every
`rating.rating` with `consumed=True` on the product, while the website list
only shows `feedback.review` with `status=approved`. Legacy/native free-form
rows could make the two disagree.

Fix (no second custom average field):

- `_deactivate_foreign_product_ratings()` — set `consumed=False` on product
  ratings with no `feedback_review_id` (or linked non-approved review)
- `_sync_approved_consumed_flags()` — align linked rows to approval state
- `_reconcile_product_native_ratings()` — bridge + fix + deactivate (idempotent)
- Called from `post_init_hook` and `migrations/19.0.2.15.0/post-migrate.py`
- Tests: `tests/test_step2_rating_consistency.py`
- Doc: `doc/STEP2_RATING_CONSISTENCY.md`

### Step 3 — Runtime / acceptance package

- `doc/STEP3_RUNTIME_ACCEPTANCE.md` — automated + manual + shell checklist
- `tools/validate_step2_step3.py` — static CI guard

Invariant after reconcile:

  product.rating_count == count(approved feedback.review for that product)

## 19.0.2.14.0 — Step 1: native review override made explicit
## 19.0.2.14.0 — Step 1: native review override made explicit

Makes the **single verified-purchase submission path** architecture explicit
and hardens the native free-form disable (no dual submission path).

### Architecture (mandatory while this module owns reviews)

```
Customer → Delivered order → feedback.request → secure token
  → feedback.review → moderation → rating.rating (consumed when approved)
  → product.template.rating_avg / rating_count
```

### Changes

- New `doc/STEP1_NATIVE_OVERRIDE.md` — decision record, disable matrix,
  enforcement points, and "if requirement changes" exit path.
- `product.template` module docstring and comments document Step 1 ownership.
- `views/website_templates.xml` header documents the single-path policy.
- `post_init_hook` re-asserts `website_sale.product_comment` inactive after
  install/upgrade (guards against view resets).
- New `tests/test_step1_native_override.py`:
  - product_comment inactive
  - `_mail_post_access == 'write'`
  - portal cannot create `rating.rating` via `message_post(rating_value=…)`
  - verified path still creates native rating on approve
- Manifest description states the single submission path explicitly.

No change to the bridge data model; Step 2 (orphan native ratings vs
approved-only list) remains next.

## 19.0.2.13.0 — Steps 6-7: automated tests & Odoo 19 validation package

Implements Steps 6 and 7 of the external 7-step plan.

### Step 6 — Automated tests (native rating bridge contract)

- New `tests/test_step6_rating_lifecycle.py` covering:
  - Review create → native `rating.rating` with `consumed=False` while pending
  - Approve → `consumed=True` → `product.rating_avg` / `rating_count` update
  - Reject / Hide → `consumed=False`, averages exclude the review
  - Multi-review average math
  - No duplicate native ratings on re-approve or `_bridge_all_approved_to_native_rating`
  - Unlink review removes linked native rating
  - Rating value updates stay on the same native row
  - Unique `feedback_review_id` constraint on `rating.rating`
  - One-review-per-request constraint
  - `feedback.review.rating` remains a related (non-stored) projection
- Registered in `tests/__init__.py`
- Complements existing `test_rating_bridge.py` and `test_review_lifecycle.py`

### Step 7 — Fresh Odoo 19 Community validation package

- New `doc/STEP7_ODOO19_VALIDATION.md`: full install → delivery → token →
  submit → moderate → approve → native stats → website display checklist,
  plus upgrade / shell / automated-test commands
- New `tools/validate_step6_step7.py`: static CI guard (test file present,
  imports, related-field contract, bridge methods, docs, manifest version)

No functional model changes in this release; architecture remains:

  feedback.review  →  rating_id  →  rating.rating (consumed gate)
  product.template.rating_avg / rating_count = native source of truth

## 19.0.2.12.0 — Steps 4-5: custom-functionality cleanup & security/workflow validation

Per an external 7-step review, re-audited Step 4 (clean up custom
functionality so the KEEP features that native Odoo doesn't provide
actually work correctly, without duplicating anything native) and Step 5
(security + workflow validation of the token system and access rights for
all four documented actors: Customer, Portal user, Internal user,
Manager/admin).

- **Step 4 fix:** `sale_order.py._compute_feedback_stats()` (sale-order
  review-completion tracking) and `feedback_review.py._recompute_vote_counts()`
  (helpful/not-helpful vote counters) were the last two call sites still
  using the deprecated `model.read_group()` API — every other aggregate in
  the module (dashboard KPIs, `res.partner` review stats) was already
  migrated to `_read_group()` in `19.0.2.10.0`. Both are now on the same
  `_read_group()` pattern; behavior is unchanged, only the ORM call.
  `tools/validate_step4_step5.py` now fails the build if `.read_group(`
  reappears anywhere under `models/`.
- **Step 4 verification (no change needed):** confirmed the rest of the
  KEEP list (verified purchase, delivery-triggered invitation, token,
  expiry/reminder, review title, moderation, helpful/not-helpful, sort/
  filter, My Reviews, dashboard, PDF/XLSX reports, REST API) does not
  duplicate any native Odoo field or model.
- **Step 5 gaps closed in the test suite** (the underlying controller code
  already implemented all of these; only test coverage was missing):
  - `tests/test_api_controller.py`: live (non-cron) expired-token rejection
    on `/api/feedback/token/<token>`; wrong-customer (403) and wrong-product
    (400) rejection on `POST /api/feedback/request` for an authenticated
    sales user.
  - `tests/test_rate_limit.py`: rate-limit coverage extended from the
    `token` route only to all four public routes (`submit`, `vote`,
    `public_get`), via a shared `_hammer()` helper.
- **Step 5 verification (no change needed):** re-confirmed ACLs/record
  rules exist for all four actors (Customer — public token via `sudo()`
  only, explicit `perm=0` ACL rows, no direct ORM access; Portal user —
  own reviews only; Internal user — read approved + own; Manager/admin —
  full access), and that `controllers/feedback_portal.py` /
  `controllers/api_controller.py` already reject invalid, expired,
  cancelled, and already-submitted tokens, and block duplicate reviews.
- Added `tools/validate_step4_step5.py`: a static CI/staging guard that
  fails on a reintroduced `.read_group()` call, a missing actor-level ACL,
  a public group gaining a non-zero permission, a rate-limit route key
  disappearing, or a controller losing its expiry/cancellation/duplicate
  guard text.
- No model, view, or migration changes; `models/sale_order.py` and
  `models/feedback_review.py` behavior is unchanged (same domains, same
  grouping, same output), so no new migration script is needed.

## 19.0.2.11.0 — Steps 1–3 re-audit: doc/architecture reconciliation

Re-ran the module's Step 1/2/3 audit (remove legacy rating duplication /
verify the native `rating.rating` bridge / confirm the native-review-UI
decision) against the current codebase, per an external 7-step review.
Runtime code already satisfied all three steps; the concrete gap found and
fixed was **stale documentation**, not stale code:

- **Step 1 (legacy rating code):** `doc/PHASE2_NATIVE_MAPPING.md` §4 and
  `doc/README.md` still described the pre-`19.0.2.9.0` design (stored
  `rating_1_count`…`rating_5_count` / `last_review_date` "retained as a
  report projection"). Those columns were actually dropped in
  `migrations/19.0.2.9.0/pre-migrate.py` and replaced by on-demand
  `_rating_get_repartition()` calls. Docs corrected to match the code and
  now explicitly flag reintroducing those columns as a Step 1 regression.
  `tools/validate_step2_native_mapping.py` extended with a guard that fails
  if those fields reappear on `product.template` or if the mapping doc
  drifts from the 19.0.2.9.0 removal again.
- **Step 2 (native rating bridge):** verified `models/rating_bridge.py`
  still enforces one `rating.rating` per `feedback.review`
  (`_feedback_review_unique`), approve → `consumed=True`,
  reject/hide → `consumed=False`, and delete → native row removed
  (`_unlink_native_rating`). No code change needed; confirmed by
  `tools/validate_step2_native_mapping.py` and `tests/test_rating_bridge.py`.
- **Step 3 (native review UI decision):** confirmed the module keeps
  verified-purchase-only reviews — native free-form submission stays
  disabled (`product.template._mail_post_access = 'write'` +
  `message_post()` guard), and the product page renders the native
  `o_website_rating_static` markup read-only via
  `customer_feedback.product_rating_compact`
  (`views/website_templates.xml`). Rationale already documented in
  `doc/PHASE2_NATIVE_MAPPING.md` §5; no behavior change.

No model, view, security, or migration changes in this release — it is a
documentation/audit-tooling correction only, so no new migration script is
needed.

## 19.0.2.10.0 — Steps 4–6: ORM, dashboard, mail access

- **Step 4:** `feedback.review.product_tmpl_id` stored related field; `product.template.review_ids` is a real `One2many` with inverse + `domain=[('status','=','approved')]` (no more computed recordset rebuild). Portal/API domains use `product_tmpl_id`.
- **Step 5:** Dashboard counts/average use `_read_group` aggregates; top/lowest products continue to use native `rating_avg` / `rating_count`. No longer loads all approved reviews into memory for KPIs.
- **Step 6:** Kept `_mail_post_access = 'write'` and `message_post()` rating_value guard with explicit regression notes; still covered by `tests/test_rating_bridge.py` (test_06, test_07). Intentional trade-off while this module owns verified-purchase reviews.
- Upgrade: `migrations/19.0.2.10.0/post-migrate.py` backfills `product_tmpl_id`.

## 19.0.2.9.0 — Steps 1–3: reuse native rating stats & reduce duplication

- **Step 1:** Removed stored `product.template.rating_1_count`…`rating_5_count`
  and `last_review_date`. Distribution is now on-demand via native
  `rating.mixin._rating_get_repartition()` (`get_rating_distribution()`).
  Last review date uses a light search (`get_last_review_date()`).
- **Step 2:** Bridge no longer copies `review_title`/`review_text` into
  `rating.rating.feedback`. Text is owned solely by `feedback.review`.
- **Step 3:** Product-page compact stars still read only native
  `rating_avg` / `rating_count`; markup aligned with Odoo website rating
  static style. Native free-form submission path remains disabled.
- Upgrade: `migrations/19.0.2.9.0/pre-migrate.py` drops the old columns.
- API / PDF / XLSX reports updated to call the new helpers.

## 19.0.2.8.0 — Phase 7: public route rate limiting

- Added process-local rate limiter (`controllers/rate_limit.py`) for public
  feedback routes (token validate, review submit, vote, public product reviews).
- Defaults (per IP / 60s window, configurable via ir.config_parameter):
  token 30, submit 10, vote 60, public_get 120.
- Public product reviews API returns 404 for unpublished products.
- Exceeded limits respond with HTTP 429.
- Closes the main open item from Phase 7 (abuse controls on CSRF-disabled
  public JSON/AJAX routes). Vote ACL remains intentional sudo-only design.

## 19.0.2.4.0 — Security, Automation & Performance hardening

- Added company isolation to feedback requests, reviews and votes.
- Hardened API authorization and same-order customer validation.
- Added race-safe duplicate handling for requests, reviews and votes.
- Switched invitation/reminder creation to Odoo's mail queue instead of synchronous SMTP sends.
- Added bounded cron batches and composite database indexes for cron/product/customer workloads.
- Added cancellation reconciliation for cancelled orders and returned/partially returned lines.
- Added cancellation handling to public token endpoints.
- Reworked sale-order feedback counters to batch ORM queries and avoid N+1 searches.

# Changelog

## 19.0.2.3.0 — Phases 4-6: model cleanup, workflow closure, website UI

Implements the three phases carried forward from doc/PHASE1_MODULE_AUDIT.md
and doc/PHASE2_NATIVE_MAPPING.md.

### Phase 4 — Model / Data Cleanup
- **Removed** the legacy duplicate fields `product.template.average_rating`,
  `total_reviews`, `review_count` (the "REMOVE candidate" from
  PHASE2_NATIVE_MAPPING.md §2 item 5). Native `rating_avg` / `rating_count`
  (bridged by `rating_bridge.py`) are now the only source of these numbers
  everywhere: backend views, the PDF report, the XLSX export wizard, the
  dashboard, and the REST API (`/api/products/<id>/reviews` keeps the same
  external JSON key names for backward compatibility with integrators).
  `migrations/19.0.2.3.0/pre-migrate.py` drops the columns cleanly on upgrade.
- `product.template._recompute_rating_stats()` rewritten to use two grouped
  `_read_group` aggregate queries instead of loading every approved review
  into Python per template — removes the O(n) per-write aggregation flagged
  in PHASE2_NATIVE_MAPPING.md §2 item 6, without changing the stored-column
  shape the reports/views depend on.
- Added missing indexes on `feedback.request` (`partner_id`, `product_id`,
  `picking_id`, `company_id`, `delivery_date`, `expiry_date`,
  `invitation_sent_date`) — all of them are scanned by the hourly / 6-hourly
  crons or common searches.
- Added explicit perm=0 ACL rows for `feedback.review.vote` under
  `base.group_portal` / `base.group_public`, documenting (rather than
  silently relying on) the sudo-only-via-controller access design flagged
  in PHASE1_MODULE_AUDIT.md §11 item 3.

### Phase 5 — Review Workflow (completion)
- Added `tests/test_review_lifecycle.py`: a single end-to-end test chaining
  every stage of the documented lifecycle — verified purchase → auto-created
  request → secure token → public portal submission → pending moderation →
  approval → native `rating.rating` sync → helpful vote → rejection removing
  the review from native averages. Closes acceptance-matrix row 20
  (doc/ACCEPTANCE_TESTS.md) with automated coverage instead of a staging-only
  manual check.

### Phase 6 — Website / eCommerce
- The AJAX sort/filter endpoint (`/feedback/product/<id>/reviews`) already
  existed on the controller, but no front-end control ever called it — the
  product page had no sort dropdown or star-rating filter UI. Added
  `product_reviews_toolbar` to `views/snippets/s_feedback_reviews.xml`
  (a "Sort by" dropdown + 5★–1★ filter chips) and extended
  `feedback_review_vote.js` to wire both to the existing endpoint and swap
  the review list in place via `fetch()`, matching the vote widget's
  no-full-reload UX.
- Added `static/src/css/feedback_reviews.css` (new frontend asset) for
  active-filter styling and small-screen layout (stacks the toolbar and lets
  the vote buttons wrap) rather than relying on default Bootstrap flex
  behaviour alone.
- Added `test_toolbar_renders_sort_and_star_filter_controls` to
  `tests/test_product_reviews_sort.py` confirming the new controls render
  with the attributes the JS expects.

## 19.0.2.2.1 — Bundle Phase 1/2 deliverables into the package

- Added `doc/PHASE1_MODULE_AUDIT.md` (Full Module Audit) and
  `doc/PHASE2_NATIVE_MAPPING.md` (Odoo 19 Native Mapping / KEEP-EXTEND-REMOVE),
  the deliverables produced ahead of the `19.0.2.2.0` architecture fix, so the
  package is self-contained: audit findings, the native-behavior verification
  that justified the Phase 3 fix, and the fix itself now travel together.
- Added `doc/README.md` as an index of progress against the 10-phase plan.
- No functional code changes in this entry.

## 19.0.2.2.0 — Phase 3: close native chatter rating bypass

Follows a source-verified audit of Odoo 19.0 core (`addons/rating`, `addons/mail`,
`addons/website_sale`) that found the Option B bridge architecture (19.0.2.0.0) was
correctly implemented, but the native free-form review path was only hidden at the
UI level, not actually closed:

- `website_sale.ProductTemplate` lowers `_mail_post_access` to `'read'` so any
  website visitor can post on a published product's chatter. Combined with the
  public `POST /mail/message/post` route and `rating` module's handling of the
  `rating_value` kwarg (`addons/rating/models/mail_thread.py`), any visitor could,
  in principle, create an unmoderated, immediately-`consumed=True` `rating.rating`
  directly — bypassing the entire invitation → token → moderation → bridge flow —
  even with `website_sale.product_comment` disabled.
- **Fix:** `product.template` now overrides `_mail_post_access` back to the
  `mail.thread` default of `'write'`, and overrides `message_post()` to strip any
  `rating_value` from non-internal / non-sudo callers as defense in depth. The
  module's own bridge (`rating_bridge.py`) is unaffected since it writes
  `rating.rating` directly under `sudo()`, not via `message_post()`.
- Added `tests/test_rating_bridge.py`: dedicated coverage for the bridge itself
  (approve → linked native rating, reject → excluded but not deleted, unlink →
  removed, idempotent re-bridge) plus regression tests for the fix above. This
  closes the "no dedicated bridge tests" gap identified in the module audit.

## 19.0.2.0.0 — Architecture refactor (Option B bridge)

### Architecture
- **Native `rating.rating` is now the source of truth** for averages and counts.
- New bridge module `models/rating_bridge.py`: every approved `feedback.review`
  creates/updates a linked `rating.rating` (res_model=`product.template`).
- Explicit dependency on Community module `rating`.
- `post_init_hook` + `migrations/19.0.2.0.0/post-migrate.py` bridge existing
  approved reviews without data loss.

### Product statistics
- Native `rating_avg` / `rating_count` preferred on website and product form.
- Legacy `average_rating` / `total_reviews` kept temporarily for upgrade safety
  and reports; distribution counts (1★–5★) remain as genuine extra stats.

### Website
- Product-page templates enhanced to read native rating fields first.
- Single coherent review experience: verified-review list enhances rather than
  replaces the native rating surface.
- Compact title rating prefers `product.rating_avg`.

### Preserved business features
- Post-delivery invitations, waiting period, expiry, reminders
- Public token links, verified purchase, moderation workflow
- Review title, helpful/not-helpful voting, sort/filter
- Portal history, dashboard, reports, API, resend wizard

### Not removed
- `feedback.review` model retained (Option B).
- No customer data deleted.

## 19.0.2.6.0 — Phase 2 Native Mapping Implementation

- Formalized the Odoo 19 Community KEEP / EXTEND / REMOVE mapping.
- Added executable `tests/test_native_mapping.py` regression coverage.
- Added `tools/validate_step2_native_mapping.py` static CI/staging guard.
- Confirmed `rating.rating` / `rating.mixin` remains the native product rating source of truth.
- Confirmed legacy product ORM duplicates (`average_rating`, `total_reviews`, `review_count`) remain removed.
- Kept the five star-count fields only as report/UI projections; they do not drive native averages.
- Documented that API keys named `average_rating` / `review_count` are response-contract names, not duplicate ORM fields.
- Kept the explicit `rating` manifest dependency.


## 19.0.2.7.0 — Phase 3 Architecture Refactor
- Made `rating.rating` the sole stored numeric rating source.
- Converted `feedback.review.rating` to a read/write related projection of `rating.rating`.
- Ensured every feedback review owns at most one native rating row, including pending/rejected reviews with `consumed=False`.
- Added native-to-business ownership link `rating.rating.feedback_review_id`.
- Added upgrade migration for existing stored review ratings.
- Removed rating duplication from the business model while retaining review workflow metadata, moderation, verified-purchase state, and text.
