# -*- coding: utf-8 -*-
"""Step 2 migration: reconcile product.template ratings with verified reviews.

After upgrade:
- Bridge any approved feedback.review missing a rating.rating
- Align consumed flags on linked rows
- Under the module's explicit exclusive product-rating ownership policy,
  set consumed=False on unowned/legacy product ratings so native
  rating_avg / rating_count match the approved verified-review list
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'feedback.review' not in env:
        _logger.warning(
            'Customer Feedback 19.0.2.15.0: feedback.review not loaded; skip reconcile')
        return
    result = env['feedback.review']._reconcile_product_native_ratings()
    _logger.info(
        'Customer Feedback 19.0.2.15.0 post-migrate reconcile: %s', result)
