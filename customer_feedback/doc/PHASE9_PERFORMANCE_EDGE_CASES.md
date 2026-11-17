# Phase 9 — Performance & Edge Cases

**Version:** 19.0.2.16.0  
**Status:** Documented + unit edge-case suite; bulk load requires staging run

---

## 1. Goals

1. Confirm the module remains correct under boundary inputs (ratings, text length, duplicates, moderation state flips).
2. Confirm native aggregates stay consistent under reconcile re-runs.
3. Provide a repeatable bulk load script for staging (10k requests / 50k reviews) without hardcoding hardware-specific pass thresholds.

---

## 2. Edge cases covered by unit tests

| Case | Test | Expected |
|------|------|----------|
| Rating &lt; 1 or &gt; 5 | `test_step6_edge_cases.test_01` | `ValidationError` |
| Review text too short/long | `test_step6_edge_cases.test_02` | `ValidationError` |
| Second review same request | `test_step6_edge_cases.test_03` | Blocked (unique request_id) |
| Reject → not in aggregates | `test_step6_edge_cases.test_04` | `consumed=False` |
| Float rating → star UI int | `test_step6_edge_cases.test_05` | `int(round(rating))` safe |
| Reconcile idempotent | `test_step6_edge_cases.test_06` | No raise; stable counts |
| force_send + deleted mail.mail | `test_step5_mail_send` | No FK crash; status updates |
| One request per order line | `test_feedback_request` | Unique constraint |
| Token uniqueness | `test_feedback_request` | Unique constraint |
| Native free-form blocked | `test_step1_native_override` | No public rating_value |

---

## 3. Performance posture (already in code)

| Area | Implementation | Notes |
|------|----------------|-------|
| Request cron batches | `_cron_batch_size()` | Bounded transactions |
| Indexes | `feedback_review_product_status_date_idx`, status+delivery on request | Hot paths |
| Native aggregates | `rating.mixin` only | No second stored average |
| Histogram | On-demand `_rating_get_repartition()` | No stored 1★–5★ columns |
| Mail | Queue for cron; force_send only for manual UI | Avoids SMTP in bulk cron |
| Votes | `_read_group` for counters | No N+1 loops |
| Dashboard / partner stats | `_read_group` | Deprecated `read_group` banned by validator |

---

## 4. Bulk load script (staging only)

```bash
./odoo-bin shell -c odoo.conf -d STAGING_DB \
  < customer_feedback/tools/perf_load_test.py
```

Script seeds ~500 products, ~2k customers, 10k requests, 50k reviews and prints wall-clock timings for create + read paths. **Never run against production.**

Record results here after staging run:

| Operation | Duration (s) | Notes |
|-----------|--------------|-------|
| Product/customer seed | | |
| Bulk requests | | |
| Bulk reviews + bridge | | |
| Product page aggregate read | | |
| Portal My Reviews | | |
| Dashboard aggregation | | |

---

## 5. Operational edge cases (manual / staging)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Waiting period not elapsed | Invitation stays pending until cron threshold |
| 2 | Token expired | Portal rejects submit |
| 3 | Token already used | Second submit blocked |
| 4 | Moderation off | Review goes straight to approved + consumed |
| 5 | Moderation on → approve | rating_count increments once |
| 6 | Hide after approve | consumed=False; count drops |
| 7 | Customer edit (if enabled) | Re-moderation or republish per settings |
| 8 | Outgoing mail server down | invitation_email_status=failed; retries up to max |
| 9 | force_send success + auto-delete mail | status=sent; invitation_mail_id empty OK |
| 10 | Multi-company | request.company_id isolates data |

---

## 6. Exit criteria for Phase 9

- [x] Edge-case unit tests present and imported
- [x] Bulk load script documented
- [ ] Staging bulk run executed and timings recorded (operator)
- [ ] No critical N+1 on product review list under moderate load (operator)

Phase 9 is **code-complete**; staging bulk sign-off remains an operator step (Phase 10).
