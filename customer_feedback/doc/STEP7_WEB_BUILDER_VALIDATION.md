# Step 7 — Website Builder options validation

Run after upgrading to **19.0.2.22.0+**. Core review workflow must stay unchanged.

## Defaults (must match pre–web-builder behaviour)

| Check | Expected |
|-------|----------|
| Product page shows reviews block | Yes (setting ON by default) |
| Title “Reviews” visible | Yes |
| Sort & filter bar visible | Yes |
| Media / verified badge / votes visible when data exists | Yes |
| Default list order | Newest |
| Voting, sort, filter, load-more AJAX | Still works |

## A. Website Builder — Customize panel

1. Open any product page → **Edit**.
2. Click the **Customer Reviews** section (`.s_feedback_reviews`).
3. Confirm the Customize panel shows:

   - Hide section title  
   - Hide sort & filter bar  
   - Hide review photos & videos  
   - Hide verified purchase badge  
   - Hide helpful votes  
   - Text align  
   - Top spacing / Bottom spacing  
   - Default sort  

4. Toggle each **Hide** option → **Save** → hard-refresh frontend.  
   Hidden parts stay hidden; unhide restores them.
5. Set **Default sort** to Highest rated → Save → refresh.  
   Sort dropdown shows Highest; list is ordered by rating (AJAX if needed).
6. Change spacing / text align → Save → refresh. Classes persist on the section.

## B. Settings — product page auto-injection

1. **Settings → Customer Feedback → Website Display**  
   - **Show Reviews on Product Pages** = OFF → Save.
2. Open a product page (frontend): reviews block must **not** appear.
3. Website Builder → drop **Customer Reviews** on a CMS page: block still works.
4. Turn setting **ON** again → product pages show the block again.

## C. Regression (must PASS)

| Area | Action | Pass if |
|------|--------|---------|
| Token submit | Submit via `/feedback/review/<token>` | Review created |
| Moderation | Approve pending review | `rating.rating` consumed; stars update |
| Votes | Helpful / Not helpful on public card | Counts update |
| Sort / filter | Change sort and star chips | List refreshes |
| Load more | Click when has_more | Extra cards append |
| Portal | My Reviews | History still listed |
| Media | Image/video on approved review | Still renders unless Hide media is on |

## D. Notes

- Options are stored as CSS classes / `data-default-sort` on `.s_feedback_reviews`.
- Hide rules use ancestor classes so AJAX-refreshed list fragments still respect them.
- Disabling auto-injection does **not** uninstall or disable the module; it only skips the product-page `t-call`.
