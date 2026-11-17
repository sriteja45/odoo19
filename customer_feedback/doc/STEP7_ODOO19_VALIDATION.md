# Step 7 — Fresh Odoo 19 Community validation

Run this checklist on a **clean Odoo 19 Community** database (or a dedicated
staging clone). Mark each row PASS / FAIL and attach logs if anything fails.

## Environment

| Item | Value |
|------|--------|
| Odoo | 19.0 Community |
| Required apps | `website_sale`, `stock`, `sale_management`, `rating`, `portal`, `mail`, `website` |
| Module | `customer_feedback` 19.0.2.16.0+ |
| Python | matches your Odoo 19 deployment |

## A. Fresh install path

```text
Install module
      ↓
Create product (storable / consu)
      ↓
Create sale order → Confirm
      ↓
Delivery completed (validate picking)
      ↓
Feedback request auto-created (token present)
      ↓
Customer opens /feedback/review/<token>
      ↓
Customer submits review (stars + title + text)
      ↓
Moderation: status = pending (if moderation enabled)
      ↓
Approve
      ↓
rating.rating created/updated, consumed=True
      ↓
product.template.rating_avg / rating_count updated
      ↓
Website product page shows stars / review list
      ↓
Reports / dashboard show the review
```

### Checklist

| # | Check | Expected | Result |
|---|--------|----------|--------|
| 1 | Module installs cleanly | No missing dependency; `rating` is a dependency | |
| 2 | Delivery creates `feedback.request` | Token, partner, product filled; status pending | |
| 3 | Token URL returns 200 | Public form loads without login | |
| 4 | Invalid token rejected | 404 / error page | |
| 5 | Expired token rejected | Rejected when expiry passed | |
| 6 | Already-used token rejected | Cannot submit twice for same request | |
| 7 | Submit creates `feedback.review` | status pending (or approved if moderation off) | |
| 8 | Native `rating.rating` linked | One row, `feedback_review_id` set, `consumed=False` while pending | |
| 9 | Approve → `consumed=True` | `product.rating_count` increments; `rating_avg` correct | |
| 10 | Reject / Hide | `consumed=False`; averages exclude the review | |
| 11 | Delete review | Linked `rating.rating` removed | |
| 12 | Website display | Stars under product name / catalog; verified badge if configured | |
| 13 | Helpful vote | Count increments | |
| 14 | No native free-form product rating form | Visitors cannot post unmoderated ratings via chatter | |

## B. Upgrade path (from 19.0.1.x / 19.0.2.x)

```bash
odoo-bin -u customer_feedback -d YOUR_DB --stop-after-init
```

| # | Check | Expected | Result |
|---|--------|----------|--------|
| 15 | Upgrade completes | No traceback | |
| 16 | Existing `feedback.review` rows preserved | Same count before/after | |
| 17 | Bridge runs | Every approved review has exactly one `rating_id` | |
| 18 | No duplicate `rating.rating` | `search_count` by product+partner stays stable across re-upgrade | |
| 19 | Averages still match | `rating_avg` / `rating_count` consistent with approved consumed ratings | |

### Shell snippet (post-upgrade)

```python
# odoo-bin shell -d YOUR_DB
Review = env['feedback.review']
Rating = env['rating.rating']
approved = Review.search([('status', '=', 'approved')])
print('approved', len(approved))
print('with rating_id', len(approved.filtered('rating_id')))
print('orphans', approved.filtered(lambda r: not r.rating_id).ids)
# duplicates?
for r in approved.filtered('rating_id'):
    twins = Rating.search([
        ('res_model', '=', 'product.template'),
        ('res_id', '=', r.product_tmpl_id.id),
        ('partner_id', '=', r.customer_id.id),
        ('feedback_review_id', '=', r.id),
    ])
    if len(twins) != 1:
        print('bad link', r.id, twins.ids)
```

## C. Automated tests (on staging / CI)

```bash
odoo-bin -d YOUR_DB -i customer_feedback --test-enable --stop-after-init \
  --test-tags=/customer_feedback
```

Critical tags / files:

- `tests/test_step6_rating_lifecycle.py` — Step 6 bridge contract
- `tests/test_rating_bridge.py` — approve / reject / unlink / portal guard
- `tests/test_review_lifecycle.py` — full HTTP happy path
- `tests/test_rate_limit.py`, `tests/test_api_controller.py` — token security

## D. Static guard (no Odoo required)

```bash
python3 tools/validate_step6_step7.py
```

Must exit 0 before shipping the zip.

## Notes

- Native Odoo remains the source of truth for `rating_avg` / `rating_count`.
- Business text, moderation, verified-purchase, tokens, votes stay on `feedback.review` / `feedback.request`.
- Live Odoo 19 Community runtime was **not** executed inside this build sandbox; mark results on your staging host.


## C. Automated test suite (Step 5 / 6)

```bash
odoo-bin -d STAGING_DB -i customer_feedback --test-enable --stop-after-init \
  --test-tags=/customer_feedback
```

Or narrower tags:

```bash
--test-tags=customer_feedback
```

Key modules:

| File | Covers |
|------|--------|
| `test_step5_mail_send.py` | force_send, FK-safe mail link |
| `test_step6_edge_cases.py` | rating bounds, text length, reconcile, stars |
| `test_step1_native_override.py` | native free-form blocked |
| `test_step2_rating_consistency.py` | native aggregates match approved |
| `test_step6_rating_lifecycle.py` | bridge lifecycle |

Static CI guards:

```bash
python3 tools/validate_step5_6_7.py
python3 tools/validate_step2_step3.py
python3 tools/validate_step6_step7.py
```

## D. Production sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Technical lead | | | PASS / FAIL |
| Product owner | | | PASS / FAIL |

Attach: install log, upgrade log, sample product page screenshot, mail delivery confirmation.
