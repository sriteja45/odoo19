import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class FeedbackReview(models.Model):
    _name = 'feedback.review'
    _description = 'Customer Product Review'
    _order = 'review_date desc'
    _rec_name = 'review_title'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    request_id = fields.Many2one('feedback.request', string='Feedback Request', required=True,
                                  ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    # Stored inverse for product.template.review_ids (step 4 ORM design).
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id', store=True, index=True, readonly=True,
    )
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    company_id = fields.Many2one('res.company', related='request_id.company_id', store=True, index=True, readonly=True)

    # Architecture: the numeric rating is owned by native rating.rating.
    # This related field is a read/write projection for business workflows;
    # it is never stored on feedback.review.
    rating = fields.Float(related='rating_id.rating', string='Rating (1-5)',
                          readonly=False, digits=(2, 1), aggregator='avg')
    review_title = fields.Char(string='Review Title')
    review_text = fields.Text(string='Review')
    review_date = fields.Datetime(string='Review Date', default=fields.Datetime.now)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Moderation'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('hidden', 'Hidden'),
    ], string='Status', default='draft', required=True, index=True)

    is_verified = fields.Boolean(string='Verified Purchase', default=True, readonly=True)
    moderation_notes = fields.Text(string='Moderation Notes')
    moderated_by = fields.Many2one('res.users', string='Moderated By', readonly=True, copy=False)

    helpful_count = fields.Integer(string='Helpful Votes', default=0, readonly=True, copy=False)
    not_helpful_count = fields.Integer(string='Not Helpful Votes', default=0, readonly=True, copy=False)
    vote_ids = fields.One2many('feedback.review.vote', 'review_id', string='Votes')

    # Step 8 — Review photos & videos (ir.attachment storage; S3-compatible
    # when the instance uses object storage for ir.attachment).
    media_ids = fields.One2many(
        'feedback.review.media', 'review_id', string='Photos & Videos',
    )
    media_count = fields.Integer(
        string='Media Count', compute='_compute_media_count', store=True,
    )

    @api.depends('media_ids')
    def _compute_media_count(self):
        for rec in self:
            rec.media_count = len(rec.media_ids)

    def get_public_media(self):
        """Return media rows safe for public product-page rendering.

        Only approved media is returned. When separate media moderation is
        off, media status tracks the parent review (approved together).
        """
        self.ensure_one()
        return self.media_ids.filtered(lambda m: m.status == 'approved')


    # NOTE: no SQL CHECK constraint on `rating` here — it is a non-stored
    # related field (related='rating_id.rating'), so there is no `rating`
    # column on the feedback_review table for PostgreSQL to check. The
    # equivalent range is enforced in Python via _check_rating() below
    # (and validated again in create() before the native row is linked).
    _one_review_per_request = models.Constraint(
        'unique(request_id)',
        'Only one review is allowed per feedback request.',
    )

    @api.model
    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute(
            'CREATE INDEX IF NOT EXISTS feedback_review_product_status_date_idx '
            'ON feedback_review (product_id, status, review_date DESC)')
        self.env.cr.execute(
            'CREATE INDEX IF NOT EXISTS feedback_review_customer_date_idx '
            'ON feedback_review (customer_id, review_date DESC)')
        return res

    @api.depends('product_id', 'customer_id')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.customer_id.name or '', rec.product_id.name or '')

    @api.constrains('rating')
    def _check_rating(self):
        for rec in self:
            if rec.rating < 1 or rec.rating > 5:
                raise ValidationError('Rating must be between 1 and 5.')

    @api.constrains('review_text')
    def _check_review_length(self):
        min_len = int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.review_min_length', default=10))
        max_len = int(self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.review_max_length', default=2000))
        for rec in self:
            if rec.review_text:
                length = len(rec.review_text)
                if length < min_len:
                    raise ValidationError('Review text must be at least %d characters.' % min_len)
                if length > max_len:
                    raise ValidationError('Review text must not exceed %d characters.' % max_len)

    @api.model_create_multi
    def create(self, vals_list):
        # rating is a related field backed by rating.rating; create the
        # business review first, then let the bridge create the native row.
        #
        # CRITICAL: the numeric score is popped from vals (related fields are
        # not stored on feedback.review) and MUST be passed explicitly to
        # _sync_native_rating(). Calling sync without rating_value reads
        # review.rating which is still empty before the native row exists,
        # so the bridge would skip and leave rating=0 / "No ratings yet".
        vals_list = [dict(vals) for vals in vals_list]
        rating_values = []
        for vals in vals_list:
            rating_value = vals.get('rating')
            if rating_value is None or not 1 <= float(rating_value) <= 5:
                raise ValidationError('Rating must be between 1 and 5.')
            rating_values.append(float(rating_value))
            vals.pop('rating', None)
        moderation_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.moderation_enabled', default='True') == 'True'
        for vals in vals_list:
            vals['status'] = 'pending' if moderation_enabled else 'approved'
        reviews = super().create(vals_list)
        for review, rating_value in zip(reviews, rating_values):
            review.request_id.write({'status': 'submitted'})
            # Bridge to native rating.rating with the score captured above.
            review._sync_native_rating(rating_value=rating_value)
            review._send_thank_you_email()
        return reviews

    def _send_thank_you_email(self):
        """Queue the thank-you email right after a review is submitted.

        Uses the native mail queue (force_send=False) instead of sending
        synchronously: review creation is often triggered from the public,
        unauthenticated portal controller (feedback_portal.py), and blocking
        that HTTP request on an outbound SMTP call is unnecessary latency/
        failure surface the module doesn't need to own. Odoo's own mail
        queue/cron already retries and tracks delivery state per mail.mail
        record - reusing that avoids duplicating the bespoke retry/status
        tracking feedback.request already implements for invitation and
        reminder emails (see _send_templated_email).

        Only template *rendering* failures are caught here and logged
        without blocking the review from being saved; delivery failures
        after the mail is queued are handled by the native mail.mail
        mechanism, not by this method.
        """
        self.ensure_one()
        template = self.env.ref('customer_feedback.mail_template_feedback_thankyou', raise_if_not_found=False)
        if not template:
            return
        try:
            template.send_mail(self.id, force_send=False, raise_exception=True)
        except Exception:
            _logger.exception(
                'Customer Feedback: failed to queue thank-you email for review %s', self.id)

    def write(self, vals):
        if self.env.context.get('skip_rating_bridge'):
            return super().write(vals)
        res = super().write(vals)
        if any(k in vals for k in ('status', 'rating', 'review_text', 'review_title')):
            self._sync_native_rating()
        # Step 8: when separate media moderation is off, keep media status
        # aligned with the parent review status.
        if 'status' in vals and not self.env.context.get('skip_media_status_sync'):
            self._sync_media_status_from_review()
        return res

    def _sync_media_status_from_review(self):
        """Propagate review status → media status unless separate moderation is on."""
        separate = self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.media_moderation_separate', 'False') == 'True'
        if separate:
            return
        for review in self:
            if not review.media_ids:
                continue
            if review.status == 'approved':
                review.media_ids.filtered(lambda m: m.status != 'approved').write(
                    {'status': 'approved'})
            elif review.status in ('rejected', 'hidden'):
                review.media_ids.filtered(lambda m: m.status != 'rejected').write(
                    {'status': 'rejected'})
            elif review.status == 'pending':
                review.media_ids.filtered(lambda m: m.status == 'approved').write(
                    {'status': 'pending'})

    def unlink(self):
        """Delete the business review while preserving native rating history.

        By default the linked native ``rating.rating`` row is retained but
        de-consumed, so deleting a review cannot silently destroy native
        rating history. A permanent purge is an explicit, internal-only
        operation via ``permanent_rating_purge`` context.
        """
        self._unlink_native_rating(
            permanent=bool(self.env.context.get('permanent_rating_purge') and self.env.su))
        return super().unlink()

    def action_approve(self):
        self.write({'status': 'approved', 'moderated_by': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'moderated_by': self.env.user.id})

    def action_hide(self):
        self.write({'status': 'hidden', 'moderated_by': self.env.user.id})

    def action_restore(self):
        """Bring a Rejected or Hidden review back to Approved (SRS Section 9/17:
        the Review Moderator actor's 'Restore Reviews' permission). Kept as a
        distinct, separately-labelled action from action_approve so moderation
        history/logging can tell an initial approval apart from a restore,
        even though both end in the same 'approved' state."""
        self.write({'status': 'approved', 'moderated_by': self.env.user.id})

    def action_customer_edit(self, vals):
        """Update rating/title/text on behalf of the customer via the public
        token-secured portal flow (see FeedbackPortalController). This updates
        the existing review in place rather than creating a new one, so the
        one-review-per-request rule is preserved. Re-runs moderation if it is
        enabled, otherwise republishes immediately. Triggers the usual
        constraints (rating range, review length) and the native rating
        bridge sync through the standard write()."""
        self.ensure_one()
        moderation_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.moderation_enabled', default='True') == 'True'
        update_vals = dict(vals)
        update_vals['review_date'] = fields.Datetime.now()
        update_vals['status'] = 'pending' if moderation_enabled else 'approved'
        self.write(update_vals)

    def _recompute_vote_counts(self):
        """Refresh the cached helpful/not-helpful counters for self from the
        underlying feedback.review.vote records. Called after every vote is
        added, changed, or retracted.

        Uses _read_group (not the deprecated read_group) - the same
        aggregate API already adopted for the dashboard (19.0.2.10.0) and
        res.partner review stats, one call per grouped field."""
        if not self:
            return
        counts = {rid: {'helpful': 0, 'not_helpful': 0} for rid in self.ids}
        for review, vote, count in self.env['feedback.review.vote']._read_group(
                [('review_id', 'in', self.ids)],
                groupby=['review_id', 'vote'],
                aggregates=['id:count']):
            if review and vote in counts.get(review.id, {}):
                counts[review.id][vote] = count
        for review in self:
            review.with_context(skip_vote_count_sync=True).write({
                'helpful_count': counts[review.id]['helpful'],
                'not_helpful_count': counts[review.id]['not_helpful'],
            })

    def get_display_name_public(self):
        """Return the customer name formatted for public website display,
        according to the 'Customer Name Display' setting (full / masked /
        anonymous). This is purely a rendering concern: the real name always
        remains in customer_id for internal/admin use."""
        self.ensure_one()
        mode = self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.anonymous_display', default='full')
        name = (self.customer_id.name or '').strip()
        if mode == 'anonymous':
            return 'Anonymous Customer'
        if mode == 'masked' and name:
            parts = name.split()
            if len(parts) >= 2 and parts[-1]:
                return '%s %s.' % (parts[0], parts[-1][0])
            return parts[0]
        return name or 'Anonymous Customer'
