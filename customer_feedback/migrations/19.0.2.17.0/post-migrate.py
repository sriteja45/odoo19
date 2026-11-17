# -*- coding: utf-8 -*-
"""19.0.2.17.0 — Option B Shared / Additive ownership default.

- Ensure ICP customer_feedback.rating_ownership defaults to 'shared'.
- Run reconcile (bridge + linked consumed flags only under shared).
- Does NOT mass-reactivate historical consumed=False ratings.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env['ir.config_parameter'].sudo()
    if not icp.get_param('customer_feedback.rating_ownership'):
        icp.set_param('customer_feedback.rating_ownership', 'shared')
        _logger.info(
            'Customer Feedback 19.0.2.17.0: set rating_ownership=shared (default)')

    if 'feedback.review' not in env:
        _logger.warning(
            'Customer Feedback 19.0.2.17.0: feedback.review not loaded; skip reconcile')
        return

    result = env['feedback.review']._reconcile_product_native_ratings()
    _logger.info(
        'Customer Feedback 19.0.2.17.0 post-migrate reconcile: %s', result)
