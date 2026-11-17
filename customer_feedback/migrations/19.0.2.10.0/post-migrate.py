# -*- coding: utf-8 -*-
"""Ensure feedback.review.product_tmpl_id is populated (step 4 inverse)."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE feedback_review fr
           SET product_tmpl_id = pp.product_tmpl_id
          FROM product_product pp
         WHERE fr.product_id = pp.id
           AND (fr.product_tmpl_id IS NULL OR fr.product_tmpl_id IS DISTINCT FROM pp.product_tmpl_id)
        """
    )
    _logger.info(
        'customer_feedback: backfilled product_tmpl_id on %s review(s)',
        cr.rowcount,
    )
