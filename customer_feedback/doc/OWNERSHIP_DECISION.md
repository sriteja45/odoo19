# Formal Decision Record — Product Rating Ownership

**Module:** Customer Feedback, Ratings & Reviews  
**Version introduced (exclusive):** 19.0.2.15.1  
**Version revised (shared default):** 19.0.2.18.0  
**Document version:** 19.0.2.18.0  
**Status:** Active — **Option B Shared / Additive is the locked default**

---

## 1. Decision summary

| Question | Answer |
|----------|--------|
| Default ownership mode while module is installed? | **shared** (additive) |
| Do existing native product ratings continue to count? | **YES** under shared |
| Are foreign / legacy product ratings deleted? | **NO** — always preserved |
| Does shared mode mass-reactivate historical `consumed=False`? | **NO** |
| Is exclusive mode available? | **YES** — explicit ICP opt-in only, requires business approval |
| Are ratings on other models (`sale.order`, etc.) touched? | **NO** — never |

Runtime source of truth for the mode:

```text
ir.config_parameter: customer_feedback.rating_ownership
  shared     ← default (missing/invalid → shared)
  exclusive  ← optional exception
```

---

## 2. Why shared is the default

Native Odoo computes `product.template.rating_avg` / `rating_count` from every
`rating.rating` row where `res_model = 'product.template'` and `consumed = True`.

Under **shared** mode this module:

1. Bridges each approved `feedback.review` to exactly one native `rating.rating`.
2. Aligns `consumed` on those linked rows with review status.
3. Leaves all other product ratings untouched so pre-existing native scores
   continue to contribute.

Exclusive mode (optional) additionally sets `consumed=False` on unowned
product ratings so that only verified approved reviews drive the stars.
That intentionally changes existing Odoo rating behaviour and must only be
enabled with explicit business sign-off.

---

## 3. What the code does

Located in `models/rating_bridge.py`:

- `_get_rating_ownership()` reads ICP; invalid/missing → `shared`.
- `_deactivate_unowned_product_ratings()` is a **no-op under shared**.
- Under exclusive only, unowned product ratings are set `consumed=False`
  (never deleted; never mass-reactivated when returning to shared).

Historical rows that were previously deactivated by an older exclusive
policy are **not** automatically restored. A separate recovery process can
be run later if the business wants those scores back.

---

## 4. Business / lead sign-off for exclusive mode

Exclusive mode must not be treated as a normal equivalent setting. Enabling it
means:

> “Only approved verified-purchase reviews from Customer Feedback will
> contribute to product.template rating_avg / rating_count. Pre-existing or
> third-party product ratings remain in the database but are excluded from
> aggregates.”

| Role | Name | Date | Signature / ticket |
|------|------|------|--------------------|
| Product Owner | ________________ | ________ | ________________ |
| Technical Lead | ________________ | ________ | ________________ |

---

## 5. Exit path

1. Set ICP `customer_feedback.rating_ownership` back to `shared` (or delete the key).
2. Deactivation stops; no automatic reactivation of historical rows.
3. Update this document and related Step docs if policy changes again.

---

## 6. Related documents

- `doc/STEP1_NATIVE_OVERRIDE.md` — native submission path exception
- `doc/STEP2_RATING_CONSISTENCY.md` — aggregate consistency rules
- `models/rating_bridge.py` — implementation of the ownership contract
