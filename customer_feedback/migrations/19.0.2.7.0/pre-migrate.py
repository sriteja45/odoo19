# -*- coding: utf-8 -*-
"""Phase 3 architecture migration.

Move the last stored feedback.review.rating value into native rating.rating
and leave feedback.review.rating as a related projection. Existing linked
rating_id values are preserved; missing links are created from the legacy
column before the ORM model is rebuilt.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'feedback_review' AND column_name = 'rating_id'
    """)
    if not cr.fetchone():
        cr.execute('ALTER TABLE feedback_review ADD COLUMN rating_id integer')

    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rating_rating' AND column_name = 'feedback_review_id'
    """)
    if not cr.fetchone():
        cr.execute('ALTER TABLE rating_rating ADD COLUMN feedback_review_id integer')

    cr.execute("SELECT id FROM ir_model WHERE model = 'product.template' LIMIT 1")
    row = cr.fetchone()
    if not row:
        _logger.warning('Customer Feedback: product.template ir.model not found; native rating migration skipped.')
        return
    res_model_id = row[0]

    cr.execute("""
        SELECT fr.id, fr.rating, fr.review_text, fr.review_title, fr.status,
               fr.customer_id, pp.product_tmpl_id
        FROM feedback_review fr
        JOIN product_product pp ON pp.id = fr.product_id
        WHERE fr.rating_id IS NULL AND fr.rating IS NOT NULL
    """)
    rows = cr.fetchall()
    for review_id, rating, review_text, review_title, status, partner_id, tmpl_id in rows:
        feedback = ((review_title or '') + ('\n\n' if review_title and review_text else '') + (review_text or '')).strip() or None
        cr.execute("""
            INSERT INTO rating_rating
                (res_model_id, res_model, res_id, partner_id, rated_partner_id,
                 rating, feedback, consumed, feedback_review_id, create_date, write_date)
            VALUES (%s, 'product.template', %s, %s, NULL, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (res_model_id, tmpl_id, partner_id, float(rating), feedback, status == 'approved', review_id))
        native_id = cr.fetchone()[0]
        cr.execute('UPDATE feedback_review SET rating_id = %s WHERE id = %s', (native_id, review_id))

    _logger.info('Customer Feedback 19.0.2.7.0: migrated %s feedback review rating(s) to native rating.rating.', len(rows))

    # The ORM will recreate the new non-stored related field `feedback.review.rating`;
    # the old physical rating column is no longer part of the architecture.
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name='feedback_review' AND column_name='rating'")
    if cr.fetchone():
        cr.execute('ALTER TABLE feedback_review DROP COLUMN rating')
        _logger.info('Customer Feedback 19.0.2.7.0: dropped legacy feedback_review.rating storage.')
