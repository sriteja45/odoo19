# Staging Validation Guide — customer_feedback 19.0.2.12.0

**Important:** Tests 1–8 cannot be marked PASS from code inspection alone.
They must be executed on a real Odoo 19 Community database.

## Prerequisites

- Odoo 19 Community (not Enterprise-only)
- Modules available: `website_sale`, `stock`, `rating`, `portal`, `mail`, `sale_management`
- PostgreSQL database (staging)
- Optional Python package: `xlsxwriter` (only for Excel reports)

## A. Fresh installation (Test 1)

```bash
# Backup first
# Install module
odoo-bin -i customer_feedback -d STAGING_DB --stop-after-init
```

Expected:
- No traceback
- Module state = installed
- `rating` is in dependency list and installed
- Models exist: feedback.request, feedback.review, feedback.review.vote

Shell check:
```python
env['ir.module.module'].search([('name','=','customer_feedback')]).state  # installed
'feedback.review' in env
'rating.rating' in env
```

## B. Upgrade from 19.0.1.8.0 (Tests 2–5)

1. Start from a DB that has customer_feedback 19.0.1.8.0 with real reviews.
2. Deploy 19.0.2.12.0 code.
3. Upgrade:

```bash
odoo-bin -u customer_feedback -d STAGING_DB --stop-after-init
```

4. Record baseline after first upgrade (shell):

```python
Review = env['feedback.review']
Rating = env['rating.rating']
approved = Review.search([('status','=','approved')])
print('feedback.review total', Review.search_count([]))
print('approved', len(approved))
print('with rating_id', len(approved.filtered('rating_id')))
print('orphans', len(approved.filtered(lambda r: not r.rating_id)))
print('rating.rating (product.template)', Rating.search_count([
    ('res_model','=','product.template'), ('consumed','=',True)]))
# product samples
for p in env['product.template'].search([('rating_count','>',0)], limit=5):
    print(p.id, p.name, 'avg', p.rating_avg, 'count', p.rating_count)
```

5. Run upgrade **again** (second time) and re-run the same print block.
   **Pass criterion:** counts of feedback.review, approved, rating_id links, and
   consumed native ratings must be **identical** to the first upgrade snapshot.

## C. Moderation (Test 7)

```python
# Pick or create a pending review
r = env['feedback.review'].search([('status','=','pending')], limit=1)
# or create via token flow
r.action_approve()
assert r.rating_id and r.rating_id.consumed is True
avg1 = r.product_id.product_tmpl_id.rating_avg

r.action_hide()
assert r.rating_id.consumed is False
# average should drop or stay consistent excluding this rating
r.product_id.product_tmpl_id.invalidate_recordset(['rating_avg','rating_count'])
avg2 = r.product_id.product_tmpl_id.rating_avg

r.action_restore()  # or action_approve
assert r.rating_id.consumed is True
```

## D. Customer journey (Test 6 + journey)

1. Confirm a sale order, validate outgoing picking → `feedback.request` created.
2. Run cron or `request.action_send_invitation()`.
3. Open token URL from email / `request.get_portal_url()`.
4. Submit stars + text.
5. `feedback.review` status pending or approved (per moderation setting).
6. Approve if pending → `rating_id` set, `consumed=True`, product average updates.
7. Open product page on website → one star block, one review list, verified badge.

## E. Website (UI)

Manual browser checks on product page:
- [ ] Exactly one star/rating display under title
- [ ] Exactly one review list (`#o_feedback_reviews`)
- [ ] No “Write a review” native free-form form
- [ ] Website editor: if “Reviews / Discussion and Rating” is turned on, still no second free-form form (safety xpath)
- [ ] Verified badge on approved reviews
- [ ] Sort: Newest / Highest / Lowest
- [ ] Filter by star
- [ ] Helpful / Not helpful
- [ ] Average shown matches backend `product.rating_avg`

## F. Idempotency table (fill on staging)

| Metric | After 1st upgrade | After 2nd upgrade | Match? |
|--------|-------------------|-------------------|--------|
| feedback.review count | | | |
| approved count | | | |
| with rating_id | | | |
| rating.rating consumed (product.template) | | | |
| sample product rating_avg | | | |
| sample product rating_count | | | |

## G. Automated helper (paste in odoo shell)

```python
def feedback_audit():
    Review = env['feedback.review']
    Rating = env['rating.rating']
    approved = Review.search([('status','=','approved')])
    linked = approved.filtered('rating_id')
    orphans = approved - linked
    consumed = Rating.search([
        ('res_model','=','product.template'),
        ('consumed','=',True),
    ])
    # potential duplicate: same partner+template+rating value
    dups = 0
    for r in linked:
        n = Rating.search_count([
            ('res_model','=','product.template'),
            ('res_id','=',r.product_id.product_tmpl_id.id),
            ('partner_id','=',r.customer_id.id),
            ('rating','=',float(r.rating)),
            ('consumed','=',True),
        ])
        if n > 1:
            dups += 1
    return {
        'review_total': Review.search_count([]),
        'approved': len(approved),
        'linked': len(linked),
        'orphans': len(orphans),
        'native_consumed': len(consumed),
        'possible_dup_groups': dups,
    }
print(feedback_audit())
```

## Pass / Fail rules

- Tests 1–8: **FAIL** until executed on staging with green results above.
- Note: the legacy duplicate fields (`average_rating`/`total_reviews`/`review_count`
  in 19.0.2.3.0, and the stored `rating_1_count`…`rating_5_count`/`last_review_date`
  histogram in 19.0.2.9.0) have already been removed from the codebase. This
  matrix still gates *upgrade/runtime* sign-off (no traceback, no orphaned
  ratings, counts match after upgrade) — it no longer gates the field removal
  itself, which is code-complete.
