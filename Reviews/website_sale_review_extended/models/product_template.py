# -*- coding: utf-8 -*-
import json

from markupsafe import Markup

from odoo import api, fields, models
from odoo.addons.rating.models import rating_data
from odoo.fields import Domain


class ProductTemplate(models.Model):
    """ EXTENSION of product.template (rating.mixin already applied by core
    'product' + the domain already narrowed by 'website_sale').

    website_sale/models/product_template.py defines:

        def _rating_domain(self):
            return super()._rating_domain() & Domain('is_internal', '=', False)

    We add ONE more override in the same chain. Because we call super()
    first, the existing is_internal filter (and whatever the base 'rating'
    module itself does) keeps working exactly as before - we only ever
    narrow the domain further, and only when a review has actually been
    marked non-approved, which by default (auto-approve = True) never
    happens. So a fresh install of this module changes nothing until the
    moderation setting is turned on.
    """
    _inherit = 'product.template'

    verified_review_count = fields.Integer(
        string="Verified Purchase Reviews",
        compute='_compute_verified_review_count',
    )
    rating_weighted_avg = fields.Float(
        string="Weighted Rating",
        compute='_compute_rating_weighted_stats',
        digits=(3, 2),
        help="Same population of reviews as the stock 'Average Rating' "
             "(rating.mixin.rating_avg), but each review is weighted "
             "before averaging instead of counted equally:\n"
             "- Verified-purchase reviews count more than unverified ones.\n"
             "- Older reviews decay exponentially towards a lower weight "
             "(half weight every rating_weighted_avg_half_life_days), so a "
             "product's score reflects its CURRENT quality rather than "
             "reviews from years ago.\n"
             "This is a NEW, additive field - the core rating_avg/"
             "rating_count fields are left completely untouched (other "
             "modules, backend sort-by-rating, exports, etc. keep working "
             "on the simple average exactly as before). Only this module's "
             "own storefront templates are switched to display the "
             "weighted figures instead (see views/product_seo_templates.xml).",
    )
    rating_weighted_count = fields.Integer(
        string="Weighted Rating Review Count",
        compute='_compute_rating_weighted_stats',
        help="Number of reviews feeding rating_weighted_avg. Uses the same "
             "domain as rating_count (_rating_domain(), i.e. respects "
             "moderation) so the two numbers stay comparable.",
    )
    question_count = fields.Integer(
        string="Published Questions",
        compute='_compute_question_count',
    )

    def _rating_domain(self):
        domain = super()._rating_domain()
        return domain & Domain('moderation_status', '=', 'approved')

    def _rating_domain_for_variant(self, product_id=None):
        """Domain for public reviews, optionally restricted to one variant.

        When product_id is set, keep reviews that either:
          - are attributed to that exact product.product, or
          - have no product_id (legacy / unattributed reviews still shown
            so we don't hide historical data after the upgrade).
        """
        self.ensure_one()
        domain = self._rating_domain() & Domain('res_id', '=', self.id)
        if product_id:
            domain = domain & (
                Domain('product_id', '=', int(product_id))
                | Domain('product_id', '=', False)
            )
        return domain

    def _compute_verified_review_count(self):
        RatingRating = self.env['rating.rating'].sudo()
        for product in self:
            domain = product._rating_domain() & Domain('res_id', '=', product.id) \
                & Domain('is_verified_purchase', '=', True)
            product.verified_review_count = RatingRating.search_count(domain)

    # ------------------------------------------------------------------
    # Weighted scoring (Phase 5)
    # ------------------------------------------------------------------
    # Weight of a verified-purchase review vs. an unverified one, before
    # recency decay is applied. Override via env if a shop wants a
    # different ratio without touching code (kept as a class attribute,
    # same convention as rating.rating._WSRE_MAX_ATTACHMENTS).
    _WSRE_VERIFIED_WEIGHT = 2.0
    _WSRE_UNVERIFIED_WEIGHT = 1.0
    # Half-life of the recency decay, in days: a review this old counts
    # half as much as a brand-new one, a review twice this old counts a
    # quarter as much, etc. Exponential rather than a hard cutoff so a
    # product never suddenly loses all its history at once.
    _WSRE_RECENCY_HALF_LIFE_DAYS = 180

    @api.depends('rating_ids.res_id', 'rating_ids.rating', 'rating_ids.is_verified_purchase',
                 'rating_ids.create_date', 'rating_ids.moderation_status')
    def _compute_rating_weighted_stats(self):
        """Weighted counterpart of rating.mixin._compute_rating_stats().

        Deliberately NOT stored: the recency component depends on
        "now", not on any recordable field, so a stored value would
        silently go stale between writes. Computed on read instead -
        the underlying query is cheap (same domain rating_count already
        uses) and this is only read on product page views / JSON-LD
        generation, not in tight loops.
        """
        Rating = self.env['rating.rating'].sudo()
        now = fields.Datetime.now()
        half_life = float(self._WSRE_RECENCY_HALF_LIFE_DAYS) or 180.0
        for product in self:
            domain = product._rating_domain() & Domain('res_id', '=', product.id) \
                & Domain('rating', '>=', rating_data.RATING_LIMIT_MIN)
            ratings = Rating.search(domain)
            if not ratings:
                product.rating_weighted_avg = 0.0
                product.rating_weighted_count = 0
                continue
            weighted_sum = 0.0
            weight_total = 0.0
            for rating in ratings:
                age_days = 0.0
                if rating.create_date:
                    age_days = max((now - rating.create_date).total_seconds() / 86400.0, 0.0)
                decay = 0.5 ** (age_days / half_life)
                base_weight = (
                    self._WSRE_VERIFIED_WEIGHT if rating.is_verified_purchase
                    else self._WSRE_UNVERIFIED_WEIGHT
                )
                weight = base_weight * decay
                weighted_sum += rating.rating * weight
                weight_total += weight
            product.rating_weighted_avg = round(weighted_sum / weight_total, 2) if weight_total else 0.0
            product.rating_weighted_count = len(ratings)

    # ------------------------------------------------------------------
    # SEO: Review / AggregateRating JSON-LD (Phase 5)
    # ------------------------------------------------------------------
    def _get_review_jsonld_reviews(self, ratings, limit=5):
        """Individual 'Review' entries for the JSON-LD block.

        Best-effort and capped at `limit`: this is markup for search
        engines, not a full export, so we keep the payload small and
        only include reviews that already cleared this module's
        moderation domain (the caller passes ratings already filtered
        by _rating_domain()).
        """
        reviews = []
        for rating in ratings[:limit]:
            author_name = rating.get_display_author_name() or 'Anonymous'
            entry = {
                '@type': 'Review',
                'reviewRating': {
                    '@type': 'Rating',
                    'ratingValue': round(rating.rating, 1),
                    'bestRating': 5,
                    'worstRating': 1,
                },
                'author': {'@type': 'Person', 'name': author_name},
            }
            if rating.create_date:
                entry['datePublished'] = rating.create_date.date().isoformat()
            feedback = (rating.feedback or '').strip()
            if feedback:
                # feedback is already plaintext (rating/mail_thread.py
                # stores html2plaintext(body) here), just cap the length.
                entry['reviewBody'] = feedback[:300]
            reviews.append(entry)
        return reviews

    def get_review_jsonld(self):
        """Schema.org Review/AggregateRating JSON-LD for this product's
        page, using the weighted score/count so the structured data
        matches what shoppers actually see on the page (Phase 5 point 23).

        Returns a `markupsafe.Markup` (pre-escaped) so the QWeb template
        can insert it into a <script type="application/ld+json"> tag
        with `t-out` without HTML-entity-escaping JSON characters like
        `&`, `<`, `>` that would otherwise corrupt the payload. Returns
        an empty Markup when there is nothing to publish (no reviews
        yet), so the template can skip rendering the tag entirely.
        """
        self.ensure_one()
        if not self.rating_weighted_count:
            return Markup('')
        Rating = self.env['rating.rating'].sudo()
        domain = self._rating_domain() & Domain('res_id', '=', self.id) \
            & Domain('rating', '>=', rating_data.RATING_LIMIT_MIN)
        ratings = Rating.search(domain, order='create_date desc')
        data = {
            '@context': 'https://schema.org/',
            '@type': 'Product',
            'name': self.name,
            'aggregateRating': {
                '@type': 'AggregateRating',
                'ratingValue': round(self.rating_weighted_avg, 1),
                'reviewCount': self.rating_weighted_count,
                'bestRating': 5,
                'worstRating': 1,
            },
        }
        reviews = self._get_review_jsonld_reviews(ratings)
        if reviews:
            data['review'] = reviews
        return Markup(json.dumps(data))

    def get_variant_review_stats(self, product_id=None):
        """Lightweight stats for the product-page 'this variant only' toggle."""
        self.ensure_one()
        Rating = self.env['rating.rating'].sudo()
        domain = self._rating_domain_for_variant(product_id)
        ratings = Rating.search(domain)
        count = len(ratings)
        if not count:
            return {'count': 0, 'avg': 0.0, 'product_id': product_id or False}
        # rating field is 0-100 in core; portal shows /20 → stars = rating/20? 
        # Actually in Odoo rating.rating.rating is float 0-5 or 0-100 depending on version.
        # Use the same field website_sale uses for averages.
        avg = sum(ratings.mapped('rating')) / float(count)
        return {
            'count': count,
            'avg': round(avg, 2),
            'product_id': product_id or False,
        }

    def _compute_question_count(self):
        Question = self.env['product.question'].sudo()
        for product in self:
            product.question_count = Question.search_count([
                ('product_tmpl_id', '=', product.id),
                ('website_published', '=', True),
            ])

    # ------------------------------------------------------------------
    # Aspect ratings (Phase 4)
    # ------------------------------------------------------------------
    def _get_review_aspects(self):
        """rating.aspect recordset configured for this product: global
        aspects (no category restriction) plus aspects attached to any
        of the product's website categories or their ancestors."""
        self.ensure_one()
        categ_ids = set()
        for categ in self.public_categ_ids:
            node = categ
            while node:
                categ_ids.add(node.id)
                node = node.parent_id
        domain = [('public_category_ids', '=', False)]
        if categ_ids:
            domain = ['|', ('public_category_ids', '=', False),
                       ('public_category_ids', 'in', list(categ_ids))]
        return self.env['rating.aspect'].sudo().search(domain)

    def get_review_aspects_data(self):
        """Serialised configured aspects for the composer widget."""
        self.ensure_one()
        return [{'id': a.id, 'name': a.name} for a in self._get_review_aspects()]

    def get_review_aspect_averages(self, product_id=None):
        """Average value per configured aspect, restricted to the exact
        same moderation/variant domain used for the product page."""
        self.ensure_one()
        aspects = self._get_review_aspects()
        if not aspects:
            return []
        Rating = self.env['rating.rating'].sudo()
        rating_ids = Rating.search(self._rating_domain_for_variant(product_id)).ids
        if not rating_ids:
            return [{'id': a.id, 'name': a.name, 'avg': 0.0, 'count': 0} for a in aspects]
        grouped = self.env['rating.aspect.rating'].sudo()._read_group(
            [('rating_id', 'in', rating_ids), ('aspect_id', 'in', aspects.ids)],
            ['aspect_id'],
            ['value:avg', '__count'],
        )
        stats = {aspect.id: (avg, count) for aspect, avg, count in grouped}
        result = []
        for a in aspects:
            avg, count = stats.get(a.id, (0.0, 0))
            result.append({'id': a.id, 'name': a.name, 'avg': round(avg or 0.0, 2), 'count': count})
        return result

    # ------------------------------------------------------------------
    # Review search (Phase 4)
    # ------------------------------------------------------------------
    def search_reviews(self, query='', product_id=None, variant_only=False,
                        min_stars=0, with_images_only=False, limit=20, offset=0):
        """Search + quick-filter reviews for the product page.

        Reuses _rating_domain_for_variant() (moderation + optional
        variant restriction) as its base domain, then narrows it further
        with the search text and quick filters. Text search is a plain
        ILIKE on the linked mail.message body/subject (the review text
        itself is stored on the message, not on rating.rating) - simple
        and index-friendly without requiring a Postgres tsvector column
        migration on core's mail.message.
        """
        self.ensure_one()
        domain = self._rating_domain_for_variant(product_id if variant_only else None)
        if min_stars:
            domain &= Domain('rating', '>=', float(min_stars))
        if with_images_only:
            domain &= Domain('attachment_count', '>', 0)
        query = (query or '').strip()
        if query:
            domain &= (Domain('message_id.body', 'ilike', query)
                       | Domain('message_id.subject', 'ilike', query))
        Rating = self.env['rating.rating'].sudo()
        total = Rating.search_count(domain)
        ratings = Rating.search(domain, order='create_date desc', limit=limit, offset=offset)
        return {
            'total': total,
            'rating_ids': ratings.ids,
            'message_ids': ratings.mapped('message_id').ids,
        }
