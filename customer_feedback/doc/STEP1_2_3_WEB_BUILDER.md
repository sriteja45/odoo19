# Steps 1–3 — Website Builder structure & options (19.0.2.23.0)

Implemented without changing core functionality (votes, sort/filter, load-more, moderation, rating bridge, token flow).

## Step 1 — Builder-aware section
- `s_feedback_reviews` section has `o_editable` and solid `data-snippet` / `data-name`.
- Editor selection affordance kept in CSS.

## Step 2 — Nested structure (still one snippet)
Clear blocks for targeting:
| Block | Class / ID | Purpose |
|-------|------------|---------|
| Title | `.o_feedback_title_block` / `.o_feedback_section_title` | Section heading |
| Toolbar | `.o_feedback_reviews_toolbar` | Sort & star filters |
| List | `#o_feedback_reviews_list_container` + `.o_feedback_list_block` | AJAX target |
| Card parts | `.o_feedback_card_stars`, `.o_feedback_card_title`, `.o_feedback_card_meta`, `.o_feedback_card_variant` | Per-field hide |

All original JS-required classes/ids are unchanged.

## Step 3 — Expanded Customize options
When the reviews section is selected in Website Builder:

**Visibility (default = visible):**
- Hide section title
- Hide sort & filter bar
- Hide review photos & videos
- Hide verified purchase badge
- Hide helpful votes
- Hide review title
- Hide author & date
- Hide purchased variant
- Hide star rating on cards

**Layout / style:**
- Card layout: Default | Compact
- Text align: Left | Center | Right
- Top / Bottom spacing
- Default sort: Newest | Highest | Lowest

Options use `data-select-class` / `data-attribute-name`. CSS rules are on the section ancestor so AJAX-refreshed cards still respect hides.

## What did **not** change
- Controllers, models, security, portal forms
- Vote / sort / filter / load-more JS behaviour
- Token submission path and moderation
- Native `rating.rating` bridge
- Product-page auto-injection setting
