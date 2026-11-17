# -*- coding: utf-8 -*-
from odoo import models


class MailMessage(models.Model):
    """ EXTENSION of mail.message as already extended by portal_rating.

    portal_rating's _portal_message_format() builds `values['rating_id']`
    from a search_read() on rating.rating restricted to
    ['id', 'publisher_comment', 'publisher_id', 'publisher_datetime',
    'message_id']. We call super() first (so the original dict is built
    exactly as before), then ADD the new keys our module needs onto that
    same dict. We never rebuild or bypass the original method.
    """
    _inherit = 'mail.message'

    def _portal_message_format(self, properties_names, options=None):
        vals_list = super()._portal_message_format(properties_names, options=options)
        if 'rating' not in properties_names:
            return vals_list

        ratings = self.env['rating.rating'].sudo().search([
            ('message_id', 'in', self.ids),
        ])
        extra_by_message_id = {}
        for r in ratings:
            extra_by_message_id[r.message_id.id] = {
                'id': r.id,
                'is_verified_purchase': r.is_verified_purchase,
                'moderation_status': r.moderation_status,
                'is_anonymous': r.is_anonymous,
                'helpful_count': r.helpful_count,
                'unhelpful_count': r.unhelpful_count,
                'attachments': r.get_attachment_data(),
                'product_id': r.product_id.id if r.product_id else False,
                'product_variant_display': r.product_variant_display or '',
                'aspect_ratings': r.get_aspect_rating_data(),
            }

        RatingVote = self.env['rating.vote']
        for message, values in zip(self, vals_list):
            extra = extra_by_message_id.get(message.id)
            if extra and values.get('rating_id'):
                values['rating_id'].update({
                    'is_verified_purchase': extra['is_verified_purchase'],
                    'moderation_status': extra['moderation_status'],
                    'is_anonymous': extra['is_anonymous'],
                    'helpful_count': extra['helpful_count'],
                    'unhelpful_count': extra['unhelpful_count'],
                    'user_vote': RatingVote._get_user_vote(extra['id']),
                    'attachments': extra['attachments'],
                    'product_id': extra['product_id'],
                    'product_variant_display': extra['product_variant_display'],
                    'aspect_ratings': extra['aspect_ratings'],
                })
        return vals_list
