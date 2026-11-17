# Step 1 — Odoo 19 Runtime Verification

This phase is now implemented as an executable staging validation harness.
It is deliberately designed to run **inside a real Odoo 19 Community environment**.
The build environment used to create this ZIP does not contain Odoo itself, so the
runtime commands cannot truthfully be marked PASS until they are executed against a
real Odoo 19 + PostgreSQL staging database.

## What the harness verifies

1. Odoo executable is version 19.
2. `customer_feedback` can be freshly installed without a traceback.
3. `customer_feedback` can be upgraded without a traceback.
4. The module's Odoo test suite executes with `--test-enable`.
5. Required models and fields are present.
6. Required dependencies (`rating`, `website_sale`, `stock`, `mail`, `portal`) are installed.
7. ACLs and record rules were loaded for feedback request/review/vote models.
8. Feedback cron and mail templates were loaded.
9. Native `rating.rating` bridge fields are available.
10. Existing data does not contain token/company-less requests or approved reviews without a native rating.

## Run

From the directory containing `customer_feedback/`:

```bash
DB_NAME=customer_feedback_staging \
ODOO_BIN=/path/to/odoo-bin \
./customer_feedback/tools/validate_step1.sh
```

With an Odoo config:

```bash
DB_NAME=customer_feedback_staging \
ODOO_BIN=/path/to/odoo-bin \
ODOO_CONFIG=/path/to/odoo.conf \
./customer_feedback/tools/validate_step1.sh
```

Use a disposable/staging database for the fresh-install step. Back up any database
that already contains customer feedback data before upgrading.

## Acceptance criterion

Step 1 is **PASS** only when the script ends with:

```text
STEP 1 COMPLETE: Odoo 19 runtime verification passed.
```

A successful static Python/XML check is not a substitute for this runtime test.
