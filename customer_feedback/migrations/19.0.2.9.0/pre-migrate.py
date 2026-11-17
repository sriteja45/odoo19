# -*- coding: utf-8 -*-
"""Drop stored histogram columns superseded by native rating repartition."""
import logging

_logger = logging.getLogger(__name__)

COLUMNS = (
    'rating_1_count',
    'rating_2_count',
    'rating_3_count',
    'rating_4_count',
    'rating_5_count',
    'last_review_date',
)


def migrate(cr, version):
    for col in COLUMNS:
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'product_template' AND column_name = %s",
            (col,),
        )
        if cr.fetchone():
            cr.execute('ALTER TABLE product_template DROP COLUMN IF EXISTS %s' % col)
            _logger.info('customer_feedback: dropped product_template.%s', col)
