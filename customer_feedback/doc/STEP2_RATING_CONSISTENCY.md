# Step 2 — Native rating consistency with approved reviews

**Version:** 19.0.2.18.0  
**Status:** Implemented / ownership policy explicit  
**Related:** `doc/OWNERSHIP_DECISION.md` (formal sign-off record)

## Problem

Native Odoo computes:

- `product.template.rating_avg`
- `product.template.rating_count`

from **all** `rating.rating` rows where `res_model='product.template'` and
`consumed=True`.

This module’s website list shows only:

```text
feedback.review WHERE status = 'approved'
```

If legacy/native free-form ratings (or unlinked rows) remain `consumed=True`,
you can get:

| Source | Count | Average |
|--------|-------|---------|
| Native stars | 5 | 4.2 |
| Verified list | 3 | 4.7 |

Under the locked shared/additive default, this is expected when legacy/native ratings coexist with verified reviews; the native aggregate is intentionally the combined source of truth. Exclusive mode is the explicit exception when the business requires verified reviews only.

## Decision

**Do not** add a second custom `average_rating` field.

The module uses the **shared / additive product-rating ownership policy by default**
(`RATING_OWNERSHIP = 'shared'`). This preserves existing native ratings while
approved verified reviews are bridged into the same native `rating.rating`
source of truth. Exclusive mode is an explicit opt-in exception.

Instead:

1. Bridge every approved `feedback.review` to exactly one `rating.rating`
   with `consumed=True`.
2. Keep non-approved linked rows with `consumed=False`.
3. Under the explicit exclusive exception, exclude any **unowned**
   product ratings from the native aggregates:
   - `res_model = product.template`
   - `consumed = True`
   - `feedback_review_id` empty **or** linked review not approved

Historical rows are retained; they simply stop contributing to aggregates.
Ratings on unrelated models are never changed.

## API

```python
env['feedback.review']._reconcile_product_native_ratings()
# → {'bridged': int, 'fixed_consumed': int, 'deactivated_foreign': int}
```

Called from:

- `post_init_hook` (install)
- `migrations/19.0.2.15.0/post-migrate.py` (upgrade)

## Invariants after reconcile

For each product template in **shared** mode:

```text
rating_count >= count(feedback.review where product_tmpl_id=X and status='approved')
```

The native aggregate may also include pre-existing native product ratings. In
**exclusive** mode, the aggregate matches the approved verified-review set.
