# Step 3 — Odoo 19 Community runtime / acceptance validation

**Version:** 19.0.2.15.0  
**Module:** customer_feedback

This is the minimum acceptance flow required after Steps 1–2.

## Prerequisites

- Odoo 19 Community
- Apps: `website_sale`, `stock`, `sale_management`, `rating`, `portal`, `mail`
- Python package: `xlsxwriter` (optional for Excel reports)

## A. Automated tests (must pass)

```bash
odoo-bin -d TEST_DB -i customer_feedback --test-enable \
  --test-tags=/customer_feedback --stop-after-init
```

Critical tags / files:

| File | Covers |
|------|--------|
| `test_step1_native_override.py` | Single path, product_comment off, message_post guard |
| `test_step2_rating_consistency.py` | Native count = approved; foreign ratings deactivated |
| `test_step6_rating_lifecycle.py` | Bridge lifecycle, consumed flags |
| `test_rating_bridge.py` | Bridge + portal rating block |
| `test_review_lifecycle.py` | End-to-end happy path |

Static CI guards (no DB required):

```bash
python3 tools/validate_step2_step3.py
python3 tools/validate_step6_step7.py
```

## B. Manual happy path (minimum)

1. **Install** module on a clean DB (or upgrade from 19.0.2.13.0+).
2. Create a storable/consu product, publish on website.
3. Create SO → Confirm → Validate delivery.
4. Confirm `feedback.request` is created (status pending/sent).
5. Open token URL from invitation (or force-send from backend).
6. Submit **5★** + review text ≥ min length.
7. Review appears **Pending** in Feedback → Reviews.
8. **Approve** the review.
9. Backend:
   - `review.rating_id.consumed == True`
   - `product.rating_count` increased by 1
   - `product.rating_avg` reflects the score
10. Website product page:
    - Stars under title match native avg/count
    - Verified review list shows the approved review
    - Native free-form form is **not** present

## C. Edge cases (minimum)

| Case | Expected |
|------|----------|
| Reject | `consumed=False`; avg/count exclude it; list hides it |
| Hide | same as reject for public |
| Restore | back to approved + consumed=True |
| Edit (if allowed) | same row; re-moderation if enabled |
| Duplicate submit same token | blocked (one review per request) |
| Invalid / expired token | error page |
| Cancelled order / returned product | no new invitation or request cancelled |
| Foreign legacy `rating.rating` on product | after reconcile, `consumed=False` |
| Helpful / Not helpful | counters update |

## D. Shell audit (staging)

```python
# odoo-bin shell -d STAGING_DB
result = env['feedback.review']._reconcile_product_native_ratings()
print(result)

# Spot-check one product
p = env['product.template'].search([('rating_count', '>', 0)], limit=1)
print(env['feedback.review']._assert_native_matches_approved(p))
```

All products with ratings should report `match=True`.

## E. Sign-off checklist

- [ ] Automated suite green
- [ ] Happy path A–B completed on staging
- [ ] Edge table C sampled
- [ ] Shell audit D: no mismatches
- [ ] Step 1: native free-form still disabled
- [ ] Step 2: no foreign consumed product ratings remain

When all boxes are checked, Steps 1–3 are complete for this module version.
