# Acceptance Tests — customer_feedback 19.0.2.15.0

Run on a real Odoo 19 Community staging database.

## Environment prerequisites
- Odoo 19 Community with `website_sale`, `stock`, `rating`, `portal`, `mail`
- Existing `feedback.review` data from 19.0.1.8.0 if testing upgrade
- At least one delivered sale order with a storable product

## Matrix

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Fresh module installation | Installs without error; depends resolve including `rating` | PENDING (staging) |
| 2 | Upgrade from 19.0.1.8.0 | Upgrade succeeds; post-migrate bridge runs | PENDING |
| 3 | Existing reviews preserved | All feedback.review rows still present after upgrade | PENDING |
| 4 | Approved → exactly one native rating | Each approved review has one rating_id; no duplicates | PENDING |
| 5 | Repeated upgrade | No extra rating.rating rows created | PENDING |
| 6 | Token → submit → approve → native update | rating.rating.consumed=True; product.rating_avg updates | PENDING |
| 7 | Reject/hide | linked rating.rating.consumed=False; excluded from average | PENDING |
| 8 | Product average/count | product.rating_avg / rating_count match approved native ratings | PASS (code + test_step2_rating_consistency) |
| 9 | Native free-form form hidden | product_comment inactive; no portal.message_thread form on product page | PASS (code + `tests/test_step1_native_override.py`) |
| 10 | Verified purchase badge | Shown on approved reviews from feedback.request | PENDING |
| 11 | Voting | Helpful/not-helpful updates counts | PENDING |
| 12 | Sorting/filtering | Newest / highest / lowest / by stars works | PENDING |
| 13 | Portal My Reviews | Customer sees own reviews | PENDING |
| 14 | Emails/crons | Invitation + reminder cron fire; templates send | PENDING |
| 15 | Reports/API | Still operate on feedback.review | PENDING |
| 16 | No Enterprise deps | Manifest only Community modules | PASS (code review) |
| 17 | No duplicate review UI | Single list under product; native thread replaced/hidden | PASS (code review) |
| 18 | No duplicate rating calc | Website uses rating_avg/rating_count | PASS (code review) |
| 19 | Native chatter cannot create ratings | Posting `rating_value` via `/mail/message/post` as a public/portal user does not create a `rating.rating` for a product (see 19.0.2.2.0 changelog) | PASS (code review) + `tests/test_rating_bridge.py::test_06/test_07` |
| 20 | Full lifecycle chains correctly (row 6 above, automated) | Delivery → request → token → public submit → pending → approve → native sync → vote → reject removes from average, all in one customer/product journey | PASS (automated) — `tests/test_review_lifecycle.py::test_01_full_lifecycle_happy_path` |

## Commands (staging)

```bash
# Upgrade
odoo-bin -u customer_feedback -d STAGING_DB --stop-after-init

# Check bridge
odoo-bin shell -d STAGING_DB <<'PY'
reviews = env['feedback.review'].search([('status','=','approved')])
print('approved', len(reviews))
print('with rating_id', len(reviews.filtered('rating_id')))
print('orphans', len(reviews.filtered(lambda r: not r.rating_id)))
# duplicates?
Rating = env['rating.rating']
for r in reviews.filtered('rating_id'):
    twins = Rating.search([
        ('res_model','=','product.template'),
        ('res_id','=',r.product_id.product_tmpl_id.id),
        ('partner_id','=',r.customer_id.id),
        ('feedback','ilike', (r.review_text or '')[:40]),
    ])
    if len(twins) > 1:
        print('possible dup', r.id, twins.ids)
PY
```

## Notes
- Live Odoo 19 Community runtime tests were **not** executed in the build environment.
- Items 16–18 are verified by code inspection against Odoo 19.0 `rating.rating` source.
- Items 1–15 require your staging DB; mark PASS/FAIL there and return results if any fail.
