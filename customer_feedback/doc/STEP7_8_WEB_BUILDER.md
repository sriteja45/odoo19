
## Step 7 implementation — Safe multi-zone / building-block mode (19.0.2.32.0)

The Customer Reviews snippet is now composed as multiple Website Builder zones:

- **Title zone** — normal editable text (`Reviews` can be renamed).
- **Toolbar zone** — the surrounding layout is editable, while the live sort/filter controls stay protected as one JS unit.
- **Before-reviews zone** — an `oe_structure` drop zone for arbitrary building blocks.
- **Reviews zone** — an editable outer layout zone containing the protected AJAX review engine.
- **After-reviews zone** — an `oe_structure` drop zone for arbitrary building blocks.

### Important safety boundary
The individual live review cards are intentionally **not** made free-form editable. Their HTML is generated from database records and replaced by AJAX during sort/filter; allowing the builder to mutate that fragment would make saved builder HTML conflict with runtime data and can break votes, filters, or load-more.

This is therefore the maximum practical Step 7 implementation that preserves existing functionality: the page becomes a composable multi-building-block layout while the dynamic review engine remains authoritative. No controller, endpoint, token, moderation, rating bridge, vote, sort/filter, or load-more code is changed.
# Steps 7–8 — Settings polish, per-page hide, regression (19.0.2.25.0)

## Step 7 — Settings & product-page injection polish

### Global switch (unchanged behaviour)
**Settings → Customer Feedback → Website Display → Show Reviews on Product Pages**
- Default **ON**: auto-inject `s_feedback_reviews` on product pages.
- **OFF**: no auto-injection; drop the snippet manually in Website Builder where needed.

### Per-page control (no core logic change)
| Goal | How |
|------|-----|
| Show only on some pages | Turn global OFF → drop snippet on those product/CMS pages |
| Hide on one product page while global ON | Edit page → select Customer Reviews → **Hide entire block on frontend** |
| Temporary hide while editing | Same option; in the editor the block stays faintly visible so it remains selectable |

Section also exposes `data-feedback-reviews="1"` for optional theme/CSS hooks.

### Unchanged
Token flow, moderation, votes, sort/filter AJAX, `rating.rating` bridge, portal.

## Step 8 — Regression & documentation

### Automated checks (`tests/test_web_builder_options.py`)
- Snippet template exists and carries `data-snippet`, `data-feedback-reviews`, list container id.
- Options view contains all hide/style/sort markers.
- List/toolbar fragments exist.
- JS-critical classes still present on the list fragment.

### Manual checklist (builder)
1. Product page → Edit → select Customer Reviews → all Customize options appear.
2. Toggle hides / card layout / title size / load-more style → Save → hard refresh → persist.
3. Sort / filter / vote / load-more still work after options applied.
4. Settings: turn Show Reviews OFF → product page has no auto block; drop snippet on a CMS page → placeholder or reviews as applicable.
5. Hide entire block on frontend → visitors do not see the section; editor still shows a dashed outline.

### Related docs
- `STEP1_2_3_WEB_BUILDER.md`
- `STEP4_5_6_WEB_BUILDER.md`
- `STEP7_WEB_BUILDER_VALIDATION.md` (earlier checklist; still valid)
