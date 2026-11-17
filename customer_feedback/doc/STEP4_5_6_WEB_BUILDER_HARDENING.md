# Steps 4–6 — Web Builder hardening (19.0.2.31.0)

Scope of this pass, as requested: implement steps 4, 5 and 6 from the
"more editable" plan, with **no functional/behavioural change** to
votes, sort, filter, load-more, moderation, the rating bridge, or the
token flow.

## Step 4 — Editor placeholder + drop zone

- The existing no-product placeholder (`.o_feedback_editor_placeholder`)
  is unchanged in appearance, but is now explicitly documented and
  tested as staying `o_not_editable` — it mirrors the real AJAX output,
  so it must never be hand-edited or it would misrepresent what
  visitors actually see.
- Added a new **drop zone**: `.o_feedback_extra_content.o_editable`,
  rendered as a sibling of `#o_feedback_reviews_list_container` (never
  nested inside it). Editors can drop a promo banner, a note, or any
  other building block there.
  - Ships empty by default → no visible or behavioural change on
    existing sites.
  - Because it lives outside the protected list container, an AJAX
    sort/filter/load-more refresh (which replaces the container's
    `innerHTML`) can never touch or erase it.
  - A CSS-only dashed-border hint ("Drop additional content here")
    appears while empty and in edit mode; it's hidden entirely on the
    live frontend (`display:none` outside `.editor_enable`).

## Step 5 — Protect critical JS hooks

The vote/sort/filter/load-more Interaction (`feedback_review_vote.js`)
already scopes its DOM queries to the closest `.s_feedback_reviews`
ancestor, so it tolerates multiple snippet instances on one page for
*behaviour*. The remaining risk was **id collisions**:

- `#o_feedback_reviews_list_container`, `#o_feedback_reviews`, and
  `#o_feedback_sort_select` (+ its `<label for="...">`) are shipped
  with fixed, human-readable ids.
- If an editor **duplicates** the section, or copies/pastes it onto
  another page, two elements can end up sharing the same id —
  breaking the `<label for>` association and any future code that
  might use `document.getElementById`.

Fix, in two layers:

1. **Build-time** (`feedback_reviews_option_plugin.js`): a new
   `_makeIdsUnique()` helper runs via `on_snippet_dropped_handlers`
   and `on_cloned_handlers`. It only rewrites an id if it detects a
   real collision on the page, keeping the first/only instance's ids
   untouched — a no-op for the common single-instance case.
2. **Runtime self-heal** (`feedback_review_vote.js`): `setup()` calls
   `_selfHealDuplicateIds()`, which performs the same collision check
   and repair. This is defense in depth for content that reaches the
   page without going through the builder hooks (imported data,
   restored backups, manual HTML edits).

No class names, data attributes, or behaviour used by the vote/sort/
filter/load-more handlers were changed — only ids that exist purely
for direct lookup / label association.

## Step 6 — AJAX reload safety after builder edits

- Confirmed (and now regression-tested) that every Customize-panel
  option is applied via classes on the **outer** `.s_feedback_reviews`
  section — never on the AJAX-managed fragment itself
  (`product_reviews_list`). That's what lets `refreshReviewList()` and
  `onLoadMoreClick()` safely replace `#o_feedback_reviews_list_container`'s
  `innerHTML` (or splice in new cards) without a style/visibility
  option ever being "undone" by the refresh — the option classes live
  one level up and are never overwritten.
- `refreshReviewList()` now also re-runs `_selfHealDuplicateIds()`
  immediately after each refresh, because the fragment it just
  injected re-renders `#o_feedback_reviews` with its plain,
  unsuffixed id — needed if a second instance of the snippet exists
  elsewhere on the same page.
- Added `tests/test_step4_5_6_web_builder_hardening.py` covering all
  of the above at the template/JS-source level (this module's test
  suite is markup/contract-based rather than live-browser, consistent
  with the existing `test_web_builder_options.py`).

## Unchanged

Votes, sort, filter, load-more behaviour, moderation, the
`rating.rating` bridge, token submit, portal, and the
`customer_feedback.show_on_product_page` settings flag are all
untouched by this pass.
