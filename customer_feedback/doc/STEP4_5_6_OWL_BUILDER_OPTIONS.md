# Steps 4–6 — Complete OWL builder options wiring (19.0.2.28.0)

Continues from `STEP1_2_3_OWL_BUILDER_OPTIONS.md`. Still **no functional change**
to reviews behaviour.

## Step 4 — Wire actions to CSS classes
All option controls use either:
- `classAction` → toggles classes already defined in `feedback_reviews.css`
- `dataAttributeAction` → sets `data-default-sort` for the frontend Interaction

Existing classes reused:
- Visibility: `o_feedback_hide_*`
- Title: `o_feedback_title_sm` / `_lg`, `o_feedback_title_primary` / `_muted`
- Cards: `o_feedback_card_compact` / `_bordered`
- Buttons: `o_feedback_filter_soft`, `o_feedback_loadmore_solid` / `_link`

## Step 5 — Special cases
| Option | Mechanism |
|--------|-----------|
| Default sort | `data-default-sort="newest\|highest\|lowest"` on section; applied once on load by `FeedbackReviewVote._applyDefaultSortFromSnippet()` |
| Text align | `o_feedback_align_center` / `o_feedback_align_right` |
| Top / Bottom spacing | `o_feedback_pt_*` / `o_feedback_pb_*` (none / sm / lg) |
| Hide entire block | `o_feedback_hide_block` + editor-only faint outline (existing CSS) |
| Editor samples | `o_feedback_hide_sample` |

Classes live on the **section** (`.s_feedback_reviews`) so AJAX-refreshed list fragments still respect them.

## Step 6 — Tests & docs
- `tests/test_web_builder_options.py` keeps the CSS-class contract checks
- This file + updated CHANGELOG

## Unchanged
Votes, sort/filter endpoints, load-more, moderation, `rating.rating` bridge,
token flow, portal, Settings auto-injection flag.
