# -*- coding: utf-8 -*-
from odoo import models


class MailThread(models.AbstractModel):
    """ EXTENSION of mail.thread, itself already extended by the 'rating'
    module (addons/rating/models/mail_thread.py) which is the piece of
    core code that actually creates a rating.rating record whenever a
    'rating_value' kwarg is passed to message_post().

    We do not duplicate or rewrite that logic. We add new whitelisted
    kwargs and, after letting the full existing super() chain run (which
    is what creates the rating and links it to the message), apply the
    extra review fields (anonymous flag, media attachments, variant).
    """
    _inherit = 'mail.thread'

    def _get_allowed_message_params(self):
        return super()._get_allowed_message_params() | {
            'is_review_anonymous',
            'review_attachment_ids',
            'review_product_id',
            'review_aspect_ratings',
        }

    def message_post(self, **kwargs):
        is_review_anonymous = kwargs.pop('is_review_anonymous', False)
        review_attachment_ids = kwargs.pop('review_attachment_ids', None) or []
        review_product_id = kwargs.pop('review_product_id', None)
        review_aspect_ratings = kwargs.pop('review_aspect_ratings', None) or {}
        message = super().message_post(**kwargs)
        rating = message.sudo().rating_id
        if not rating:
            return message
        vals = {}
        if is_review_anonymous:
            vals['is_anonymous'] = True
        if review_product_id and not rating.product_id:
            try:
                vals['product_id'] = int(review_product_id)
            except (TypeError, ValueError):
                pass
        if review_attachment_ids:
            # Link pre-uploaded ir.attachment records (created by the
            # multipart upload route) onto the rating.
            att_ids = [int(x) for x in review_attachment_ids if x]
            if att_ids:
                vals['attachment_ids'] = [(6, 0, att_ids)]
                # Also attach them to the message so core chatter shows them.
                message.sudo().write({
                    'attachment_ids': [(4, aid) for aid in att_ids],
                })
        if vals:
            rating.write(vals)
        # Fallback: still try purchase-history lookup if product_id empty
        if not rating.product_id and rating.res_model == 'product.template' and rating.res_id and rating.partner_id:
            variant = rating._find_purchased_variant(rating.res_id, rating.partner_id)
            if variant:
                rating.product_id = variant.id
        if review_aspect_ratings:
            rating._set_aspect_ratings(review_aspect_ratings)
        return message
