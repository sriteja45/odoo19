# -*- coding: utf-8 -*-
"""Bridge between feedback.review and native rating.rating (Odoo 19 Community).

Verified against Odoo 19.0 addons/rating/models/rating.py:
- rating.rating fields used: res_model_id, res_model, res_id, partner_id,
  rating, feedback, consumed, rated_on
- Averages (rating_avg / rating_count) only include rows with consumed=True
  (see rating.mixin._rating_domain)
- is_internal is a related field on message_id; we do NOT write it directly.
  Public visibility is controlled via consumed=True/False.

Ownership policy (Option B — Shared / Additive, default):
  Native rating.rating remains the single source of truth for numeric scores
  and product.template aggregates (rating_avg, rating_count,
  _rating_get_repartition). Approved feedback.review rows are bridged into
  native ratings and contribute alongside any existing/unowned product
  ratings that are already consumed=True.

  Default mode is **shared**: unowned/legacy product ratings are left
  untouched (no deactivation). Exclusive mode is an optional, explicit
  opt-in that excludes unowned product.template ratings from aggregates; it
  must only be enabled with business approval.

  This module never mass-reactivates historical consumed=False rows when
  switching to shared mode.

  Formal decision record: doc/OWNERSHIP_DECISION.md
  Native submission exception: doc/STEP1_NATIVE_OVERRIDE.md
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# ICP key for runtime ownership mode (shared | exclusive).
RATING_OWNERSHIP_PARAM = 'customer_feedback.rating_ownership'
RATING_OWNERSHIP_DEFAULT = 'shared'


class RatingRating(models.Model):
    _inherit = 'rating.rating'

    feedback_review_id = fields.Many2one(
        'feedback.review', string='Feedback Review', copy=False, index=True,
        ondelete='set null', readonly=True,
        help='Business review that owns this native rating, when applicable.',
    )

    _feedback_review_unique = models.Constraint(
        'unique(feedback_review_id)',
        'A native rating can be linked to only one feedback review.',
    )


class FeedbackReview(models.Model):
    _inherit = 'feedback.review'

    # Ownership mode is read from ir.config_parameter at runtime.
    # Default is shared (additive). Exclusive is an explicit opt-in.
    # Kept as a class attribute only for backward-compatible test access;
    # prefer _get_rating_ownership() everywhere.
    RATING_OWNERSHIP = RATING_OWNERSHIP_DEFAULT

    rating_id = fields.Many2one(
        'rating.rating',
        string='Native Rating',
        copy=False,
        index=True,
        ondelete='set null',
        help='Linked Odoo native rating.rating. '
             'Native averages use only consumed=True ratings.',
    )

    @api.model
    def _get_rating_ownership(self):
        """Return runtime ownership mode: 'shared' (default) or 'exclusive'.

        Missing or invalid ICP values safely fall back to shared so a
        malformed configuration cannot accidentally activate exclusive
        deactivation of unowned native ratings.
        """
        value = self.env['ir.config_parameter'].sudo().get_param(
            RATING_OWNERSHIP_PARAM, RATING_OWNERSHIP_DEFAULT)
        if value not in ('shared', 'exclusive'):
            return RATING_OWNERSHIP_DEFAULT
        return value


    def _native_rating_vals(self, consumed=None, rating_value=None):
        """Build values for the native rating source of truth.

        Numeric rating + consumed flag only. Full review title/body live on
        feedback.review (single source of truth for text). We intentionally
        do NOT copy review_text into rating.rating.feedback to avoid storing
        the same content twice.
        """
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id
        if rating_value is None:
            rating_value = self.rating
        if consumed is None:
            consumed = self.status == 'approved'
        return {
            'res_model_id': self.env['ir.model']._get_id('product.template'),
            'res_model': 'product.template',
            'res_id': tmpl.id,
            'partner_id': self.customer_id.id,
            'rated_partner_id': False,
            'rating': float(rating_value),
            # Leave feedback empty: business text is owned by feedback.review
            'feedback': False,
            'consumed': bool(consumed),
            'feedback_review_id': self.id,
        }

    def _sync_native_rating(self, rating_value=None):
        """Synchronize the business review to exactly one native rating row.

        feedback.review owns business metadata/workflow; rating.rating owns
        the actual numeric rating and all native aggregates. Non-approved
        reviews keep a native row with consumed=False so moderation can change
        state without creating duplicate rating records.
        """
        Rating = self.env['rating.rating'].sudo()
        for review in self:
            value = rating_value if rating_value is not None else review.rating
            if not value:
                continue
            vals = review._native_rating_vals(
                consumed=review.status == 'approved', rating_value=value)
            if review.rating_id:
                review.rating_id.write(vals)
            else:
                native = Rating.create(vals)
                review.with_context(skip_rating_bridge=True).write({
                    'rating_id': native.id,
                })

    def _unlink_native_rating(self, permanent=False):
        """Preserve native rating history when a business review is removed.

        Normal deletion only de-consumes the linked native rating. Physical
        deletion is reserved for an explicit internal purge operation.
        """
        ratings = self.mapped('rating_id').sudo()
        if not ratings:
            return
        if permanent and self.env.su:
            ratings.unlink()
        else:
            ratings.write({'consumed': False})

    @api.model
    def _bridge_all_approved_to_native_rating(self):
        """Idempotent: bridge approved reviews that lack a native rating."""
        to_bridge = self.search([
            ('status', '=', 'approved'),
            ('rating_id', '=', False),
        ])
        if not to_bridge:
            _logger.info('Customer Feedback: no approved reviews need bridging.')
            return 0
        _logger.info(
            'Customer Feedback: bridging %s approved review(s) to rating.rating',
            len(to_bridge),
        )
        bridged = 0
        for review in to_bridge:
            try:
                review._sync_native_rating()
                bridged += 1
            except Exception:
                _logger.exception(
                    'Customer Feedback: failed to bridge review %s', review.id)
        return bridged

    # ------------------------------------------------------------------
    # Step 2 — Native aggregate consistency
    # ------------------------------------------------------------------

    @api.model
    def _domain_foreign_product_ratings(self):
        """Product ratings that are NOT owned by an approved feedback.review.

        Used only when ownership mode is exclusive, to find consumed ratings
        that would otherwise contribute to rating_avg/rating_count alongside
        (or instead of) verified reviews.
        """
        return [
            ('res_model', '=', 'product.template'),
            ('consumed', '=', True),
            '|',
            ('feedback_review_id', '=', False),
            ('feedback_review_id.status', '!=', 'approved'),
        ]

    @api.model
    def _deactivate_unowned_product_ratings(self):
        """Exclude unowned product ratings when ownership mode is exclusive.

        Default mode is **shared**: this method is a no-op and leaves all
        existing native product ratings untouched.

        Exclusive mode (explicit ICP opt-in only) sets consumed=False on
        product.template ratings that are not linked to an approved
        feedback.review. Ratings are never deleted and unrelated res_models
        are never touched.

        This method never mass-reactivates historical consumed=False rows.
        """
        ownership = self._get_rating_ownership()
        if ownership != 'exclusive':
            _logger.info(
                'Customer Feedback: rating ownership=%s; leaving unowned '
                'product ratings untouched.',
                ownership,
            )
            return 0

        Rating = self.env['rating.rating'].sudo()
        foreign = Rating.search(self._domain_foreign_product_ratings())
        if not foreign:
            _logger.info(
                'Customer Feedback: no unowned product ratings to deactivate.')
            return 0
        _logger.info(
            'Customer Feedback: exclusive ownership policy deactivating %s '
            'unowned/legacy product rating(s) (consumed=False); ratings are '
            'preserved for history.',
            len(foreign),
        )
        foreign.write({'consumed': False})
        return len(foreign)

    @api.model
    def _deactivate_foreign_product_ratings(self):
        """Backward-compatible alias for the ownership deactivation method."""
        return self._deactivate_unowned_product_ratings()

    @api.model
    def _sync_approved_consumed_flags(self):
        """Ensure every linked rating matches the review's approved state."""
        reviews = self.search([('rating_id', '!=', False)])
        fixed = 0
        for review in reviews:
            should_consume = review.status == 'approved'
            if bool(review.rating_id.consumed) != should_consume:
                review.rating_id.sudo().write({'consumed': should_consume})
                fixed += 1
        if fixed:
            _logger.info(
                'Customer Feedback: fixed consumed flag on %s linked rating(s)',
                fixed,
            )
        return fixed

    @api.model
    def _reconcile_product_native_ratings(self):
        """Full reconciliation (idempotent).

        1. Bridge approved reviews missing a native row.
        2. Align consumed flags on already-linked rows.
        3. Under exclusive ownership only: exclude unowned product.template
           ratings from native aggregates (retained for history). Under
           shared (default) this step is a no-op.
        """
        bridged = self._bridge_all_approved_to_native_rating()
        fixed = self._sync_approved_consumed_flags()
        deactivated = self._deactivate_unowned_product_ratings()
        # Invalidate native aggregates on affected templates
        Rating = self.env['rating.rating'].sudo()
        tmpl_ids = Rating.search([
            ('res_model', '=', 'product.template'),
        ]).mapped('res_id')
        if tmpl_ids:
            self.env['product.template'].browse(tmpl_ids).invalidate_recordset(
                ['rating_avg', 'rating_count'])
        _logger.info(
            'Customer Feedback: reconcile done (ownership=%s, bridged=%s, '
            'fixed_consumed=%s, deactivated_foreign=%s)',
            self._get_rating_ownership(), bridged, fixed, deactivated,
        )
        return {
            'bridged': bridged,
            'fixed_consumed': fixed,
            'deactivated_foreign': deactivated,
            'ownership': self._get_rating_ownership(),
        }

    @api.model
    def _assert_native_matches_approved(self, product_tmpl):
        """Helper for tests: compare native count to approved review count.

        Under exclusive mode, match means equality (unowned excluded).
        Under shared mode, native count may be higher than approved count
        because existing unowned ratings also contribute.
        """
        product_tmpl.ensure_one()
        product_tmpl.invalidate_recordset(['rating_avg', 'rating_count'])
        approved = self.search_count([
            ('product_tmpl_id', '=', product_tmpl.id),
            ('status', '=', 'approved'),
        ])
        ownership = self._get_rating_ownership()
        if ownership == 'exclusive':
            match = product_tmpl.rating_count == approved
        else:
            # Shared: native must at least include all approved reviews.
            match = product_tmpl.rating_count >= approved
        return {
            'approved_reviews': approved,
            'rating_count': product_tmpl.rating_count,
            'rating_avg': product_tmpl.rating_avg,
            'ownership': ownership,
            'match': match,
        }

