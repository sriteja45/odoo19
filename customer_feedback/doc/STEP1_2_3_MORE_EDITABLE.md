# Steps 1–3 — More editable Website Builder structure (19.0.2.30.0)

Implemented without changing any functional behaviour.

## What changed

### Step 1 — Relax toolbar protection
- Removed the outer `<div class="o_not_editable">` around the toolbar.
- Toolbar is now selectable as part of the section.
- Internal filter buttons and sort `<select>` remain JS-bound and work as before.

### Step 2 — Nested editable zones
- Title block (`.o_feedback_title_block`) now has `o_editable`.
- Clear structure:
  - Title block → editable
  - Toolbar wrap → selectable
  - List container (`#o_feedback_reviews_list_container`) → still `o_not_editable` (AJAX safety)

### Step 3 — Options plugin improvement
- Added secondary OWL option component for the title block.
- Main section options remain unchanged and fully functional.

## What did **not** change (functionality preserved)
- Votes (helpful / not helpful)
- Sort & filter AJAX
- Load more
- Moderation workflow
- Rating bridge (`rating.rating`)
- Token submission path
- Portal “My Reviews”
- Settings auto-injection toggle
- All existing CSS class-based Customize options

## Why list stays non-editable
The review list is replaced via AJAX. Making it fully free-form editable would break sort/filter/load-more. This is intentional and required for stable functionality.
