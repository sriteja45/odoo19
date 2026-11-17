# website_sale_review_extended

Custom Odoo 19 module that closes the gap between Odoo's **built-in**
eCommerce review system and Amazon/Flipkart-style reviews — by **extending**
the stock `rating`, `portal_rating` and `website_sale` modules, never by
replacing them.

This module was built against the actual Odoo **19.0** source
(`addons/rating`, `addons/portal_rating`, `addons/website_sale`,
`addons/sale`) to make sure every inherited model, view and template
reference is real, not guessed.

---

## Existing Feature Reuse & Extension Rule — compliance map

| Requirement | How this module complies |
|---|---|
| Reuse existing feature as-is if it satisfies the requirement | Star-rating submission, the review textarea, photo/video **attachment upload** (paperclip button in the composer), the chatter thread, and the publisher-comment feature are all left completely untouched — they already work and are reused as-is. |
| Extend rather than reimplement if the existing feature is insufficient | Every new capability (verified purchase, moderation, voting, anonymous posting, review-request emails) is added as new **fields + methods on the existing `rating.rating`, `mail.thread`, `mail.message`, `product.template`, `sale.order`, `sale.order.line`, `res.config.settings` models**, using `_inherit`, and every overridden method calls `super()` first. |
| Never discard/rebuild without technical justification | The only two genuinely **new** objects are `rating.vote` (no equivalent exists anywhere in core to extend — there is no per-user "was this helpful" concept in `rating.rating`) and one `ir.cron` + `mail.template` record (reusing the standard cron/email framework, not a custom mailer). Both are documented inline in the code with the justification. |
| No duplicate logic / no conflicts with standard architecture | `product.template._rating_domain()` is extended in the *same override chain* `website_sale` already uses (calls `super()`, then narrows further). With default settings (auto-approve = on) the added filter is a no-op, so a fresh install changes **zero** visible behaviour until you turn moderation on. |

---

## What's inside

```
website_sale_review_extended/
├── models/
│   ├── rating_rating.py        # + is_verified_purchase, moderation_status,
│   │                            #   is_anonymous, helpful_count, unhelpful_count
│   ├── rating_vote.py          # NEW small model: one row per (review, voter)
│   ├── mail_thread.py          # + is_review_anonymous kwarg support
│   ├── mail_message.py         # exposes the new fields to the existing widget
│   ├── product_template.py     # extends _rating_domain(), + verified_review_count
│   ├── sale_order.py           # + "Review Requests" smart button
│   ├── sale_order_line.py      # + review_requested tracking, cron helper
│   └── res_config_settings.py  # + 3 toggles, reusing config_parameter fields
├── controllers/
│   └── review_controller.py    # NEW /website_sale/review/vote route
├── data/
│   ├── mail_template_data.xml  # "Rate your purchase" email (mail.template)
│   └── ir_cron_data.xml        # daily cron calling the existing helper
├── views/
│   ├── rating_rating_views.xml # inherits rating's own list/form/search/action
│   ├── sale_order_views.xml    # inherits sale's own form view
│   └── res_config_settings_views.xml  # inherits website_sale's own settings block
└── static/src/
    ├── xml/review_message_patch.xml     # t-inherit mail.Message (badges + votes)
    ├── xml/review_composer_patch.xml    # t-inherit mail.Composer (anon checkbox)
    ├── js/review_message_patch.js       # patch(Message.prototype, ...)
    └── js/review_composer_patch.js      # patch(Composer.prototype, ...)
```

## Features added

1. **Verified Purchase badge** — computed from real `sale.order.line`
   delivery data (`state = 'sale'`, `qty_delivered > 0`), not just self-reported.
2. **Review moderation queue** — optional pending/approved/rejected workflow,
   with an "Approve / Reject" action on the existing backend rating form and
   a *Reviews to Moderate* menu under **Website ▸ eCommerce**.
3. **Helpful / Not helpful voting** — one vote per customer per review,
   toggleable, shown on the product page next to each review.
4. **Anonymous posting** — optional checkbox in the review composer; masks
   the reviewer's display name via `rating.get_display_author_name()` and
   flags the review with a "Posted Anonymously" badge.
5. **Automated review-request emails** — daily cron (configurable delay,
   default 7 days after delivery) plus a manual "Send Review Request"
   button on confirmed sales orders. Uses the standard `mail.template` +
   `ir.cron` framework.
6. **Settings** — three new toggles added directly into the existing
   Website ▸ Configuration ▸ Settings ▸ eCommerce block (not a separate page).

## Installation

1. Copy the `website_sale_review_extended` folder into your Odoo 19
   `addons` path.
2. Update the apps list, then install **"Website Sale Review Extended"**.
3. Go to **Website ▸ Configuration ▸ Settings ▸ eCommerce** to turn on
   moderation and/or automated review-request emails.

## Known caveats / please test before production

- The **frontend OWL template patches** (`static/src/xml/*.xml`,
  `static/src/js/*.js`) target the internal `mail.Message` / `mail.Composer`
  component structure as it exists in the Odoo **19.0** branch snapshot this
  module was built against. Odoo occasionally adjusts internal chatter
  component markup between point releases (19.0 → 19.1, etc.) — if you're
  on a different Odoo 19 build, verify the two `t-inherit` xpaths still
  match, and adjust if needed. The **backend** models/views/settings/cron
  have no such risk; they use stable, documented APIs.
- `is_anonymous` currently masks the name only in places that call
  `rating.get_display_author_name()` (backend) and shows a "Posted
  Anonymously" badge on the frontend; it does not yet substitute the
  masked name into the chatter's own author-name binding (that binding is
  owned by core `mail.Message` and tied to `author_id`, not to
  `rating_id`). Treat it as a moderation signal today; swapping the
  displayed name is a reasonable next iteration if you need it.
## Phase 1 — Rich Media (implemented)

1. **`attachment_ids` many2many** on `rating.rating` with size/mimetype
   validation in `create`/`write` (max 5 files, 10 MiB, images + common
   video types).
2. **HTTP multipart upload route** `/website_sale/review/upload` (JSON-RPC
   cannot carry binary payloads). Returns attachment ids + access tokens.
3. **Composer JS** — drag-and-drop + file picker, client-side preview
   thumbnails, upload-before-submit, passes `review_attachment_ids` into
   `message_post`.
4. **Message template** — thumbnail grid under each review + vanilla JS
   lightbox (keyboard arrows / Escape).
5. **Backend form** — "Review Media" notebook page with kanban preview
   for moderators; list column + "With Media" search filter.

Core still attaches files to `mail.message` as well (so the chatter paperclip
continues to work); the explicit link on `rating.rating` is what powers the
public grid, validation, and moderator preview.

## Phase 2 — Variant Attribution (implemented)

1. **`product_id`** (`product.product`) on `rating.rating` alongside core `res_id`
   (template). Stored **`product_variant_display`** for the public badge.
2. **Auto-populated** at create time from the partner's most recent delivered
   SO line for that template; also accepted via `review_product_id` on
   `message_post` (composer resolves the selected combination on the product page).
3. **`product.template._rating_domain_for_variant(product_id)`** — filters to
   that variant while still including legacy reviews with no `product_id`.
4. **Frontend badge** — attribute values shown next to the Verified Purchase badge.
5. **"This variant only" toggle** — public widget injects a checkbox above the
   review chatter; query param `wsre_variant_only=1` + AJAX call to
   `/website_sale/review/filter`.

## Phase 3 — Q&A Engine (implemented)

1. **Models** — `product.question`, `product.answer`, plus lightweight upvote
   join tables `product.question.vote` / `product.answer.vote`. Access rules
   for public (read), portal (read+create), internal users (full).
2. **Routes** — `/website_sale/question/ask`, `/answer`, `/upvote`, `/list`
   (jsonrpc).
3. **Product page** — Q&A section after `#product_detail` with ask form,
   question list, answer form, upvote buttons (`product_qa.js`).
4. **Notification** — `mail_template_product_question` emails the product
   responsible / company when a new question is created (same mail.template
   pattern as review-request emails).

Backend menu: **Website ▸ eCommerce ▸ Product Questions**.

## Phase 4 — Search & Aspect Ratings (implemented)

1. **Search route** — `/website_sale/review/search` (public, jsonrpc). Builds
   on the same `product.template._rating_domain_for_variant()` used
   everywhere else in this module, then narrows it with a plain ILIKE on the
   linked `mail.message` body/subject (the review text lives on the message,
   not on `rating.rating`, so that's the actual field searched) plus the
   quick filters below. Returns matching `rating_ids` / `message_ids` + a
   total count.
2. **Frontend search bar** — `review_search_filter.js` injects a debounced
   (350 ms) search input above the review chatter and hides/shows message
   DOM nodes by id, the same pattern `review_variant_filter.js` already uses
   for the Phase 2 toggle. It reads that toggle's state too, so "search" and
   "this variant only" compose instead of fighting over the same nodes.
3. **Quick filters** — "With images only" (`attachment_count > 0`) and a
   minimum-stars button group (All / 4+ / 3+ / 1+), wired to the exact same
   `/website_sale/review/search` call as the text search.
4. **`rating.aspect`** (name, free-text category label, website categories)
   + **`rating.aspect.rating`** (aspect, review, 1-5 value) — no equivalent
   in core, which only ever stores one overall score per review.
5. **Per-category configuration** — `product.public.category.aspect_ids`
   (inverse m2m), configurable from either the aspect form or the category
   form; child categories inherit their parent's aspects. An aspect with no
   categories applies to every product.
6. **Composer UI** — `review_composer_patch.js/.xml` fetch the configured
   aspects for the product via `/website_sale/review/aspects` and render an
   optional star picker per aspect; rated aspects ride along in
   `postData.review_aspect_ratings` and are written via the same
   `mail.thread.message_post()` extension point Phase 1/2 already use
   (`models/mail_thread.py`), validated server-side against the product's
   actually-configured aspects before being saved.

Aspect averages are also exposed (`product.template.get_review_aspect_averages()`)
so a future summary widget ("Comfort: 4.2/5 · 38 ratings") can be built
without any further backend work; the current release surfaces per-review
aspect stars on each message and the composer picker, but does not yet
render a product-level aspect summary block.

Backend menu: **Website ▸ eCommerce ▸ Review Aspects**.

## Phase 5 — SEO + Weighted Scoring (implemented)

1. **JSON-LD** — `product.template.get_review_jsonld()` builds a
   `Product` / `AggregateRating` (+ up to 5 `Review`) schema.org block,
   inserted via `views/product_seo_templates.xml` (`t-inherit` of
   `website_sale.product`, anchored on the always-present
   `product.website_description` div - not on the optional "Discussion
   and Rating" snippet, so it appears even on stores that keep that
   block disabled). Returns a pre-escaped `markupsafe.Markup` so the
   `<script type="application/ld+json">` tag isn't HTML-entity-mangled
   by `t-out`.
2. **`product.template.rating_weighted_avg` / `rating_weighted_count`** —
   a NEW, additive pair of fields (compute, not stored - the recency
   term depends on "now"). Verified-purchase reviews are weighted 2×
   unverified ones; every review's weight additionally decays
   exponentially with age (180-day half-life). Core's own
   `rating_avg`/`rating_count` are left completely alone.
3. **Storefront migration** — `views/product_seo_templates.xml` also
   `t-inherit`s `website_sale.product_title` (product page) and
   `website_sale.products_item` (shop grid tile) to swap the two
   `t-set` values feeding `portal_rating.rating_widget_stars_static`
   from `rating_avg`/`rating_count` to the weighted pair, so what
   shoppers see matches the JSON-LD. Backend list/kanban "Average
   Rating", sort-by-rating on `/shop`, and anything else built on the
   stock fields are unaffected - only these two storefront snippets
   were touched.
4. **Anti-spam** — `rating.rating._wsre_check_review_spam()`, called
   from `create()` for every product-review vals dict:
   - **Rate limit (hard block)**: raises `ValidationError` - so no row
     is ever created - once the same partner and/or request IP has
     posted `review_spam_rate_limit_count` reviews (default 5) within
     `review_spam_rate_limit_window_minutes` (default 60). Both
     settings are exposed under **Website ▸ Configuration ▸ Settings ▸
     eCommerce ▸ Review Anti-Spam**.
   - **Duplicate content (soft flag)**: a SHA-256 of the normalised
     review text (≥ 20 chars, to avoid false positives on short generic
     reviews) is compared against the last 30 days of reviews. A match
     sets `is_flagged_duplicate = True` and forces
     `moderation_status = 'pending'` - even with auto-publish on -
     instead of rejecting the review, since two genuine customers can
     honestly write near-identical short reviews. Toggle via the same
     Settings page; flagged reviews get their own list/search filter
     (**Flagged Duplicate**) next to the existing moderation ones.
   - `submission_ip` is stored on the review (when available - empty
     for backend-created ratings, e.g. imported data) purely for
     rate-limiting and moderator investigation, not shown publicly.
