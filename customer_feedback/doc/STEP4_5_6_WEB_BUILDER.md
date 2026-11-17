# Steps 4–6 — Richer styles, dynamic safety, editor placeholder (19.0.2.24.0)

## Step 4 — Richer Customize options
All options are class-based on `.s_feedback_reviews`. Defaults leave the previous UI unchanged.

| Option | Values |
|--------|--------|
| Title size | Small / Medium (default) / Large |
| Title color | Default / Primary / Muted |
| Card layout | Default / Compact / Bordered cards |
| Filter button style | Outline (default) / Soft fill |
| Load more button | Outline primary (default) / Solid primary / Link style |

Plus all previous visibility toggles, text align, spacing, default sort.

## Step 5 — Dynamic content safety
- Hide and style classes are applied to the **section** (`.s_feedback_reviews`), not to the list fragment.
- After AJAX refresh of `#o_feedback_reviews` / `.o_feedback_review_list`, CSS still applies via the ancestor.
- Controllers, vote endpoints, sort/filter URLs unchanged.

## Step 6 — Editor affordances
- No product context → dashed placeholder + two sample skeleton cards (layout preview only).
- “Hide editor placeholder samples” option removes the skeleton.
- Hint text explains that real reviews show on product pages / via Settings auto-injection.

## Unchanged
Votes, sort, filter, load-more behaviour, moderation, `rating.rating` bridge, token submit, portal, settings flag `customer_feedback.show_on_product_page`.
