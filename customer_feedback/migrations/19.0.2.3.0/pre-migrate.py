# -*- coding: utf-8 -*-
"""Phase 4 (Model/Data Cleanup) upgrade step.

product.template.average_rating / total_reviews / review_count are removed
from the model in this version (see models/product_template.py). Native
rating_avg / rating_count (from rating.mixin, bridged by rating_bridge.py)
have been the real source of truth since 19.0.2.0.0 and have been verified
in production per doc/PHASE1_MODULE_AUDIT.md and doc/PHASE2_NATIVE_MAPPING.md,
so no data needs to be copied anywhere before dropping these columns - unlike
the 19.0.2.0.0 upgrade (which bridged *review* data into rating.rating), this
step only removes redundant *derived* statistics that are trivially
recomputable from feedback.review + rating.rating if ever needed again.

Run as pre-migrate (before the ORM registry is rebuilt with the new model
definition) so the columns are gone before Odoo tries to reconcile the
model against a schema that no longer declares them - this avoids relying
on _auto_init's own (slower, less explicit) implicit column removal and
keeps the upgrade footprint self-documented here instead.
"""
import logging

_logger = logging.getLogger(__name__)

LEGACY_COLUMNS = ('average_rating', 'total_reviews', 'review_count')


def migrate(cr, version):
    for column in LEGACY_COLUMNS:
        cr.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'product_template' AND column_name = %s",
            (column,),
        )
        if cr.fetchone():
            _logger.info(
                'Customer Feedback 19.0.2.3.0: dropping legacy column '
                'product_template.%s (superseded by native rating_avg/rating_count).',
                column,
            )
            cr.execute('ALTER TABLE product_template DROP COLUMN %s' % column)
