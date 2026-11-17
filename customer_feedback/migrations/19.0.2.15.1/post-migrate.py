# -*- coding: utf-8 -*-
"""19.0.2.15.1 migration: enforce the explicit product-rating ownership policy.

The implementation now makes ownership explicit in rating_bridge.py. The
existing reconciliation remains idempotent and preserves rating rows; it only
excludes unowned product.template ratings from native aggregates because the
module's product-review ownership is explicitly exclusive.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'feedback.review' not in env:
        _logger.warning(
            'Customer Feedback 19.0.2.15.1: feedback.review not loaded; '
            'skip rating ownership reconciliation')
        return

    result = env['feedback.review']._reconcile_product_native_ratings()
    _logger.info(
        'Customer Feedback 19.0.2.15.1 ownership reconciliation: %s', result)
