# -*- coding: utf-8 -*-
"""Product template extensions for verified-purchase reviews (Step 1).

ARCHITECTURE (single submission path — see doc/STEP1_NATIVE_OVERRIDE.md)
=======================================================================
This module owns the eCommerce product-review experience. Public submission
is ONLY:

  Delivered order → feedback.request (token) → feedback.review → moderation
  → rating.rating (consumed=True when approved) → native rating_avg/count

Native free-form product reviews are disabled:
  - website_sale.product_comment is forced inactive
  - _mail_post_access = 'write' (blocks public/portal chatter posts)
  - message_post() strips rating_value for non-internal callers

Native Odoo remains the source of truth for averages:
  rating_avg, rating_count, _rating_get_repartition()
"""
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ------------------------------------------------------------------
    # Step 1 — Extend the native review experience: restrict free-form submission.
    #
    # website_sale sets _mail_post_access = 'read' so any visitor can post
    # on product chatter and create unmoderated rating.rating rows. We
    # restore 'write' so only internal users can post. Combined with
    # message_post() stripping untrusted rating_value, the public mail
    # route cannot create product ratings outside the verified bridge.
    #
    # This is intentional while the module owns verified-purchase reviews.
    # Covered by tests/test_rating_bridge.py (test_06, test_07) and
    # tests/test_step1_native_override.py.
    # ------------------------------------------------------------------
    _mail_post_access = 'write'

    # Real inverse One2many (step 4). Domain limits the form/snippet to
    # approved reviews; backend moderation menus use feedback.review actions
    # without this domain. Inverse field is feedback.review.product_tmpl_id.
    review_ids = fields.One2many(
        'feedback.review',
        'product_tmpl_id',
        string='Verified Reviews',
        domain=[('status', '=', 'approved')],
        copy=False,
    )


    PUBLIC_REVIEW_PAGE_SIZE = 20
    PUBLIC_REVIEW_SORTS = {
        'newest': 'review_date desc, id desc',
        'highest': 'rating desc, review_date desc, id desc',
        'lowest': 'rating asc, review_date desc, id desc',
    }

    def get_public_review_page(self, sort='newest', ratings=None, limit=None, offset=0):
        """Return a bounded page of approved public reviews.

        This is the single review-list query helper used by both the initial
        product-page render and the AJAX endpoint, preventing unbounded
        one2many/search loads while keeping website sorting/filtering in one
        place.
        """
        self.ensure_one()
        try:
            limit = max(1, min(int(limit or self.PUBLIC_REVIEW_PAGE_SIZE), 100))
        except (TypeError, ValueError):
            limit = self.PUBLIC_REVIEW_PAGE_SIZE
        try:
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            offset = 0

        domain = [
            ('product_tmpl_id', '=', self.id),
            ('status', '=', 'approved'),
        ]
        if ratings:
            normalized = set()
            for value in ratings:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    continue
                if 1 <= value <= 5:
                    normalized.add(value)
            if normalized:
                domain.append(('rating', 'in', sorted(normalized)))

        order = self.PUBLIC_REVIEW_SORTS.get(sort, self.PUBLIC_REVIEW_SORTS['newest'])
        rows = self.env['feedback.review'].sudo().search(
            domain, order=order, limit=limit + 1, offset=offset)
        has_more = len(rows) > limit
        return {
            'reviews': rows[:limit],
            'has_more': has_more,
            'next_offset': offset + limit if has_more else None,
            'limit': limit,
            'offset': offset,
        }

    def get_rating_distribution(self):
        """Return {1: n, 2: n, …, 5: n} using native rating.mixin repartition.

        Approved feedback.review rows are bridged to rating.rating with
        consumed=True, so native repartition matches the moderated set.
        """
        self.ensure_one()
        if not hasattr(self, '_rating_get_repartition'):
            return {i: 0 for i in range(1, 6)}
        repartition = self._rating_get_repartition()
        result = {i: 0 for i in range(1, 6)}
        for key, count in (repartition or {}).items():
            try:
                star = int(round(float(key)))
            except (TypeError, ValueError):
                continue
            if star in result:
                result[star] = int(count)
        return result

    def get_last_review_date(self):
        """Latest approved feedback.review date (business layer)."""
        self.ensure_one()
        review = self.env['feedback.review'].sudo().search([
            ('product_tmpl_id', '=', self.id),
            ('status', '=', 'approved'),
        ], order='review_date desc', limit=1)
        return review.review_date if review else False

    def message_post(self, **kwargs):
        """Step 1 defense-in-depth: strip untrusted rating_value.

        Only the moderated bridge (sudo / internal) may create product
        ratings. Portal and public callers cannot inject a consumed native
        rating through the generic chatter mechanism.
        """
        if kwargs.get('rating_value') and not self.env.su and not self.env.user.has_group('base.group_user'):
            kwargs = dict(kwargs)
            kwargs.pop('rating_value', None)
        return super().message_post(**kwargs)

    def action_view_reviews(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'customer_feedback.action_feedback_review')
        action['domain'] = [('product_tmpl_id', '=', self.id)]
        action['context'] = {
            'default_product_id': self.product_variant_id.id,
            'default_product_tmpl_id': self.id,
        }
        return action


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_view_reviews(self):
        """Delegate to product.template — form may open as product.product."""
        self.ensure_one()
        return self.product_tmpl_id.action_view_reviews()
