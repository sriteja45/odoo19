# Phase 3 — Architecture Refactor

## Target architecture

`rating.rating` is the single source of truth for the numeric score and native aggregates. `feedback.review` is the business-review layer containing verified-purchase context, moderation state, title/text, voting, and request linkage.

### Ownership
- `feedback.review.rating_id` links to exactly one `rating.rating`.
- `feedback.review.rating` is a non-stored read/write related projection of `rating.rating.rating`.
- `rating.rating.feedback_review_id` links the native rating back to its business review.
- `rating.rating.consumed` controls whether the score contributes to Odoo's native `rating_avg`/`rating_count`.
- Pending/rejected/hidden reviews retain their native row with `consumed=False`; approved reviews use `consumed=True`.

## What remains custom
- feedback request/token and verified-delivery logic
- moderation workflow
- review title/text and customer-facing business metadata
- helpful/not-helpful votes
- reporting/histogram projections

## What is not duplicated
- numeric rating storage
- native average/count
- native product rating aggregation

Odoo 19's `rating.mixin` computes `rating_avg` and `rating_count` from `rating.rating`, filtered to consumed ratings.


## Reporting note
The business review rating projection is intentionally non-stored. Pivot/graph views therefore do not aggregate `feedback.review.rating`; native product rating analysis should use `product.template.rating_avg`, `product.template.rating_count`, or the native `rating.rating` model. This avoids reintroducing a second stored numeric rating source.
