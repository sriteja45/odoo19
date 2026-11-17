# Steps 1–3 — Odoo 19 OWL Website Builder options (19.0.2.27.0)

Restores full Customize-panel editability for the Customer Reviews snippet
**without changing any product-review functionality**.

## What was done

### Step 1 — OWL Option Component + Plugin
- `static/src/builder/plugins/feedback_reviews_option_plugin.js`
- `FeedbackReviewsOption` extends `BaseOptionComponent`
- Selector: `.s_feedback_reviews`
- Plugin registered in `registry.category("website-plugins")`

### Step 2 — Options UI template
- `static/src/builder/plugins/feedback_reviews_option.xml`
- Visibility checkboxes (title, toolbar, media, verified, votes, card fields, sample, entire block)
- Title size / title color / card layout / filter style / load-more style selects
- All actions are pure CSS class toggles already supported by `feedback_reviews.css`

### Step 3 — Asset registration
- Added to `website.website_builder_assets` in `__manifest__.py`
  (required for builder plugins in Odoo 19)

## Unchanged
- Controllers, models, security, portal forms
- Vote / sort / filter / load-more JS behaviour
- Token submission path and moderation
- Native `rating.rating` bridge
- Product-page auto-injection setting
- Existing CSS class contract

## How to verify
1. Upgrade module to 19.0.2.27.0
2. Open a product page → Edit
3. Select the Customer Reviews block
4. Customize panel should show Visibility, Title, Title color, Card layout, Filter button style, Load more button
5. Toggle options → Save → hard refresh → classes persist
6. Sort / filter / vote / load-more still work
