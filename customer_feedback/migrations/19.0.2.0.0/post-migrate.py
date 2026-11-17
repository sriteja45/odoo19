# -*- coding: utf-8 -*-
"""Upgrade to 19.0.2.0.0: bridge existing approved reviews to rating.rating.

Safe and idempotent. Does not delete any feedback.review rows.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'feedback.review' not in env:
        return
    Review = env['feedback.review']
    if not hasattr(Review, '_bridge_all_approved_to_native_rating'):
        _logger.warning(
            'Customer Feedback: bridge method missing; skip migration.')
        return
    Review._bridge_all_approved_to_native_rating()
    _logger.info('Customer Feedback 19.0.2.0.0: post-migrate bridge complete.')
