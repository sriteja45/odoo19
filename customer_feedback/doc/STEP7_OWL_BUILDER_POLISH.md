# Step 7 — Website Builder polish (19.0.2.29.0)

Final builder UX polish. **No functional change** to reviews.

## What changed

1. **Editable title**  
   The “Reviews” heading stays a normal text node so users can rename it in the Website Builder.

2. **Protected dynamic zones**  
   Toolbar and review list carry `o_not_editable` so the editor does not treat AJAX-replaced markup as free HTML (prevents broken sort/filter/vote).

3. **Clearer editor hints**  
   - Placeholder text explains Customize options + Settings auto-injection.  
   - When “Hide entire block on frontend” is on, the editor shows a faint dashed outline and a short label.

4. **Settings (unchanged behaviour, already present)**  
   - Global: Settings → Customer Feedback → Show Reviews on Product Pages.  
   - Per-page: snippet option “Hide entire block on frontend”.

## Unchanged
Votes, sort/filter AJAX, load-more, moderation, `rating.rating` bridge, token flow, portal, auto-injection logic.
