# -*- coding: utf-8 -*-
import hashlib
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RatingRating(models.Model):
    """ EXTENSION of the stock 'rating.rating' model (addons/rating).

    We do not touch any existing field, method or behaviour of the core
    model. We only ADD fields and, where necessary, extend a method by
    calling super() first so the original logic always still runs.
    """
    _inherit = 'rating.rating'

    # ------------------------------------------------------------------
    # Verified Purchase (Amazon/Flipkart-style badge)
    # ------------------------------------------------------------------
    is_verified_purchase = fields.Boolean(
        string="Verified Purchase",
        compute='_compute_is_verified_purchase',
        store=True,
        help="True if the reviewing customer has an actually delivered/"
             "invoiced Sales Order line for the reviewed product. "
             "Odoo core has no equivalent field - stock reviews cannot be "
             "trusted to come from an actual buyer.",
    )

    @api.depends('res_model', 'res_id', 'partner_id', 'product_id')
    def _compute_is_verified_purchase(self):
        SaleOrderLine = self.env['sale.order.line'].sudo()
        for rating in self:
            verified = False
            if rating.res_model == 'product.template' and rating.res_id and rating.partner_id:
                domain = [
                    ('order_id.state', '=', 'sale'),
                    ('qty_delivered', '>', 0),
                    ('product_id.product_tmpl_id', '=', rating.res_id),
                    ('order_partner_id.commercial_partner_id', '=',
                     rating.partner_id.commercial_partner_id.id),
                ]
                # Prefer exact variant match when product_id is known
                if rating.product_id:
                    domain.append(('product_id', '=', rating.product_id.id))
                verified = bool(SaleOrderLine.search_count(domain, limit=1))
            rating.is_verified_purchase = verified

    # ------------------------------------------------------------------
    # Moderation workflow (approve / reject before publication)
    # ------------------------------------------------------------------
    moderation_status = fields.Selection(
        selection=[
            ('approved', 'Approved'),
            ('pending', 'Pending Approval'),
            ('rejected', 'Rejected'),
        ],
        string="Moderation Status",
        default=lambda self: self._default_moderation_status(),
        index=True,
        help="Controls whether the review is publicly visible on the "
             "product page. Stock Odoo has no moderation queue at all; "
             "every submitted review is shown immediately. This field is "
             "consumed by product.template._rating_domain() (see "
             "product_template.py in this module) which is itself an "
             "EXTENSION of the existing domain method, not a replacement.",
    )
    moderated_by_id = fields.Many2one('res.users', string="Moderated By", readonly=True, copy=False)
    moderated_date = fields.Datetime(string="Moderated On", readonly=True, copy=False)
    moderation_reason = fields.Char(string="Rejection Reason", copy=False)

    def _default_moderation_status(self):
        auto_approve = self.env['ir.config_parameter'].sudo().get_param(
            'website_sale_review_extended.auto_approve_reviews', 'True') == 'True'
        if auto_approve or self.env.user.has_group('website.group_website_restricted_editor'):
            return 'approved'
        return 'pending'

    def action_approve_review(self):
        self.write({
            'moderation_status': 'approved',
            'moderated_by_id': self.env.user.id,
            'moderated_date': fields.Datetime.now(),
        })

    def action_reject_review(self):
        self.write({
            'moderation_status': 'rejected',
            'moderated_by_id': self.env.user.id,
            'moderated_date': fields.Datetime.now(),
        })

    def action_reset_to_pending(self):
        self.write({
            'moderation_status': 'pending',
            'moderated_by_id': False,
            'moderated_date': False,
        })

    # ------------------------------------------------------------------
    # Anonymous posting
    # ------------------------------------------------------------------
    is_anonymous = fields.Boolean(
        string="Post Anonymously",
        default=False,
        help="When set, the reviewer's name is masked on the public "
             "product page (e.g. 'A***  V.'). The underlying partner_id "
             "is preserved for internal traceability/moderation.",
    )

    def get_display_author_name(self):
        """Reusable helper for both backend and (via the mail.message
        extension) the frontend widget, so masking logic lives in one
        place instead of being duplicated in templates."""
        self.ensure_one()
        if not self.is_anonymous or not self.partner_id:
            return self.partner_id.name or ''
        name = self.partner_id.name or ''
        parts = name.split()
        if not parts:
            return 'Anonymous'
        masked = parts[0][0] + '*' * max(len(parts[0]) - 1, 1)
        if len(parts) > 1:
            masked += ' ' + parts[-1][0] + '.'
        return masked

    # ------------------------------------------------------------------
    # Variant attribution (Phase 2)
    # ------------------------------------------------------------------
    # Core stores res_model/res_id pointing at product.template. We also
    # keep the concrete product.product the reviewer bought so the
    # frontend can show an attribute badge and filter "this variant only".
    product_id = fields.Many2one(
        'product.product',
        string="Product Variant",
        index=True,
        ondelete='set null',
        help="The specific product.product variant this review is about. "
             "res_id still points at the product.template (as core does).",
    )
    product_variant_display = fields.Char(
        string="Variant Attributes",
        compute='_compute_product_variant_display',
        store=True,
        help="Human-readable attribute values (e.g. 'Color: Red, Size: M') "
             "for the public badge.",
    )

    @api.depends('product_id', 'product_id.product_template_attribute_value_ids')
    def _compute_product_variant_display(self):
        for rating in self:
            display = ''
            product = rating.product_id
            if product and product.product_template_attribute_value_ids:
                # Prefer the same short label Odoo uses on the product form
                parts = []
                for ptav in product.product_template_attribute_value_ids:
                    attr = ptav.attribute_id.name or ''
                    value = ptav.name or ''
                    if attr and value:
                        parts.append('%s: %s' % (attr, value))
                    elif value:
                        parts.append(value)
                display = ', '.join(parts)
            elif product and product.display_name and product.product_tmpl_id:
                # Fallback: strip template name from display_name if present
                tmpl_name = product.product_tmpl_id.name or ''
                full = product.display_name or ''
                if tmpl_name and full.startswith(tmpl_name):
                    display = full[len(tmpl_name):].strip(' -()')
                else:
                    display = full
            rating.product_variant_display = display or False

    def _find_purchased_variant(self, product_tmpl_id, partner):
        """Return the most recently delivered product.product the partner
        bought for this template, or empty recordset."""
        if not product_tmpl_id or not partner:
            return self.env['product.product']
        line = self.env['sale.order.line'].sudo().search([
            ('order_id.state', '=', 'sale'),
            ('qty_delivered', '>', 0),
            ('product_id.product_tmpl_id', '=', product_tmpl_id),
            ('order_partner_id.commercial_partner_id', '=',
             partner.commercial_partner_id.id),
        ], order='id desc', limit=1)
        return line.product_id if line else self.env['product.product']

    # ------------------------------------------------------------------
    # Helpful / Not helpful voting
    # ------------------------------------------------------------------
    vote_ids = fields.One2many('rating.vote', 'rating_id', string="Votes")
    helpful_count = fields.Integer(compute='_compute_vote_counts', store=True, string="Helpful Votes")
    unhelpful_count = fields.Integer(compute='_compute_vote_counts', store=True, string="Not Helpful Votes")

    @api.depends('vote_ids.vote_type')
    def _compute_vote_counts(self):
        for rating in self:
            rating.helpful_count = len(rating.vote_ids.filtered(lambda v: v.vote_type == 'helpful'))
            rating.unhelpful_count = len(rating.vote_ids.filtered(lambda v: v.vote_type == 'unhelpful'))

    # ------------------------------------------------------------------
    # Rich media attachments (Phase 1)
    # ------------------------------------------------------------------
    # Explicit many2many on the rating itself (core attaches files to
    # mail.message only). Used for validation, backend preview, and the
    # public thumbnail grid. Keeps a stable link even if the message is
    # edited or the attachment is detached from the chatter.
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'rating_rating_ir_attachment_rel',
        'rating_id',
        'attachment_id',
        string="Review Media",
        help="Photos and videos attached to this product review. "
             "Validated for size and mimetype on create/write.",
    )
    attachment_count = fields.Integer(
        compute='_compute_attachment_count',
        string="Media Count",
        store=True,
    )

    # Hard limits — override via ir.config_parameter if needed later.
    _WSRE_ALLOWED_MIMETYPES = frozenset({
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/webm', 'video/quicktime',
    })
    _WSRE_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MiB
    _WSRE_MAX_ATTACHMENTS = 5

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rating in self:
            rating.attachment_count = len(rating.attachment_ids)

    def _validate_review_attachments(self, attachments):
        """Raise ValidationError if any attachment exceeds size/mimetype/count rules."""
        if not attachments:
            return
        if len(attachments) > self._WSRE_MAX_ATTACHMENTS:
            raise ValidationError(
                "A review may include at most %s media files." % self._WSRE_MAX_ATTACHMENTS
            )
        for att in attachments:
            mimetype = (att.mimetype or '').split(';')[0].strip().lower()
            if mimetype not in self._WSRE_ALLOWED_MIMETYPES:
                raise ValidationError(
                    "Unsupported file type '%s' for '%s'. Allowed: images (JPEG, PNG, GIF, WebP) "
                    "and videos (MP4, WebM, QuickTime)." % (mimetype or 'unknown', att.name or 'file')
                )
            # file_size is stored on ir.attachment; fall back to datas length if missing
            size = att.file_size or 0
            if not size and att.datas:
                import base64
                try:
                    size = len(base64.b64decode(att.datas))
                except Exception:
                    size = 0
            if size > self._WSRE_MAX_ATTACHMENT_SIZE:
                raise ValidationError(
                    "File '%s' is too large (%s bytes). Maximum size is %s MiB."
                    % (att.name or 'file', size, self._WSRE_MAX_ATTACHMENT_SIZE // (1024 * 1024))
                )

    @api.model_create_multi
    def create(self, vals_list):
        # Pre-fill product_id from purchase history when not provided
        for vals in vals_list:
            if vals.get('product_id'):
                continue
            if vals.get('res_model') != 'product.template':
                continue
            res_id = vals.get('res_id')
            partner_id = vals.get('partner_id')
            if not res_id or not partner_id:
                continue
            partner = self.env['res.partner'].browse(partner_id)
            variant = self._find_purchased_variant(res_id, partner)
            if variant:
                vals['product_id'] = variant.id
        # Anti-spam (Phase 5): hard rate-limit + soft duplicate-content
        # flag. Runs on every product-review vals dict, before the
        # record actually exists, so a blocked submission never creates
        # a row at all.
        for vals in vals_list:
            self._wsre_check_review_spam(vals)
        records = super().create(vals_list)
        for rating in records:
            if rating.attachment_ids:
                rating._validate_review_attachments(rating.attachment_ids)
            # If create-time vals had no partner/res yet, try once more after super
            if not rating.product_id and rating.res_model == 'product.template' and rating.res_id and rating.partner_id:
                variant = self._find_purchased_variant(rating.res_id, rating.partner_id)
                if variant:
                    rating.product_id = variant.id
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            for rating in self:
                rating._validate_review_attachments(rating.attachment_ids)
        return res

    # ------------------------------------------------------------------
    # Anti-spam (Phase 5)
    # ------------------------------------------------------------------
    submission_ip = fields.Char(
        string="Submission IP",
        readonly=True,
        copy=False,
        help="Request IP address at the time the review was submitted, "
             "when available. Used for rate-limiting; also useful to "
             "moderators investigating a suspected bot/spam burst.",
    )
    feedback_hash = fields.Char(
        string="Feedback Hash",
        index=True,
        readonly=True,
        copy=False,
        help="SHA-256 of the normalised (lowercased, whitespace-collapsed) "
             "review text. Left empty for reviews with no/short text - "
             "only used to detect near-identical copy-pasted content, not "
             "to identify short generic reviews like 'Great!'.",
    )
    is_flagged_duplicate = fields.Boolean(
        string="Flagged as Duplicate Content",
        readonly=True,
        copy=False,
        help="Set automatically when this review's text hash matches "
             "another recent review. Does not hide the review, it just "
             "forces moderation_status back to 'pending' (even if "
             "auto-approve is on) so a human takes a look.",
    )

    # Rate-limit / duplicate-detection tuning. Also exposed as
    # ir.config_parameter via res.config.settings so a shop can adjust
    # them without a code change - see models/res_config_settings.py.
    _WSRE_SPAM_RATE_LIMIT_COUNT = 5
    _WSRE_SPAM_RATE_LIMIT_WINDOW_MINUTES = 60
    _WSRE_SPAM_DUPLICATE_LOOKBACK_DAYS = 30
    _WSRE_SPAM_DUPLICATE_MIN_LENGTH = 20

    def _wsre_get_spam_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            rate_limit_count = int(ICP.get_param(
                'website_sale_review_extended.spam_rate_limit_count',
                self._WSRE_SPAM_RATE_LIMIT_COUNT))
        except (TypeError, ValueError):
            rate_limit_count = self._WSRE_SPAM_RATE_LIMIT_COUNT
        try:
            rate_limit_minutes = int(ICP.get_param(
                'website_sale_review_extended.spam_rate_limit_window_minutes',
                self._WSRE_SPAM_RATE_LIMIT_WINDOW_MINUTES))
        except (TypeError, ValueError):
            rate_limit_minutes = self._WSRE_SPAM_RATE_LIMIT_WINDOW_MINUTES
        duplicate_check_enabled = ICP.get_param(
            'website_sale_review_extended.spam_duplicate_check_enabled', 'True') == 'True'
        return {
            'rate_limit_count': max(rate_limit_count, 0),
            'rate_limit_minutes': max(rate_limit_minutes, 1),
            'duplicate_check_enabled': duplicate_check_enabled,
        }

    def _wsre_get_request_ip(self):
        """Best-effort request IP, empty outside an HTTP request context
        (e.g. reviews created from the backend or via server actions)."""
        try:
            from odoo.http import request
            if request and request.httprequest:
                return request.httprequest.remote_addr or False
        except RuntimeError:
            pass
        return False

    def _wsre_normalize_feedback_hash(self, text):
        """SHA-256 of the normalised review text, or False if there's no
        text or it's too short to be a meaningful duplicate signal."""
        if not text:
            return False
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        if len(normalized) < self._WSRE_SPAM_DUPLICATE_MIN_LENGTH:
            return False
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _wsre_check_review_spam(self, vals):
        """Anti-spam gate applied to a not-yet-created rating.rating
        `vals` dict (mutated in place with submission_ip/feedback_hash/
        is_flagged_duplicate before create() runs).

        - Hard rate limit: raises ValidationError - and therefore blocks
          the whole submission - if the same partner and/or the same
          request IP has posted at least N reviews in the last M
          minutes. Keyed on partner OR ip (whichever are available) so
          neither a shared office IP nor a partner posting through two
          browsers slips past the other check.
        - Soft duplicate flag: never blocks. Two different customers can
          honestly both write "Great product, fast delivery!" - so a
          text-hash match only forces the review to moderation_status
          'pending' (overriding auto-approve) instead of being rejected
          outright. Reviews shorter than
          _WSRE_SPAM_DUPLICATE_MIN_LENGTH are never hashed/flagged.
        """
        if vals.get('res_model') != 'product.template':
            return
        config = self._wsre_get_spam_config()
        partner_id = vals.get('partner_id')
        ip = self._wsre_get_request_ip()
        vals['submission_ip'] = ip

        if config['rate_limit_count'] and (partner_id or ip):
            window_start = fields.Datetime.now() - timedelta(minutes=config['rate_limit_minutes'])
            partner_leaf = ('partner_id', '=', partner_id) if partner_id else None
            ip_leaf = ('submission_ip', '=', ip) if ip else None
            if partner_leaf and ip_leaf:
                identity_domain = ['|', partner_leaf, ip_leaf]
            else:
                identity_domain = [partner_leaf or ip_leaf]
            recent_count = self.sudo().search_count(
                ['&', ('create_date', '>=', window_start)] + identity_domain
            )
            if recent_count >= config['rate_limit_count']:
                raise ValidationError(
                    "You've submitted too many reviews recently. Please "
                    "wait a while before posting another one."
                )

        feedback_hash = self._wsre_normalize_feedback_hash(vals.get('feedback'))
        vals['feedback_hash'] = feedback_hash
        if feedback_hash and config['duplicate_check_enabled']:
            lookback_start = fields.Datetime.now() - timedelta(
                days=self._WSRE_SPAM_DUPLICATE_LOOKBACK_DAYS)
            is_duplicate = bool(self.sudo().search_count([
                ('feedback_hash', '=', feedback_hash),
                ('create_date', '>=', lookback_start),
            ]))
            if is_duplicate:
                vals['is_flagged_duplicate'] = True
                vals['moderation_status'] = 'pending'

    # ------------------------------------------------------------------
    # Aspect ratings (Phase 4)
    # ------------------------------------------------------------------
    # One line per (aspect, review). Kept as a separate model (see
    # models/rating_aspect.py) instead of dynamic fields on rating.rating
    # so aspects can be reconfigured per category without any schema
    # migration here.
    aspect_rating_ids = fields.One2many(
        'rating.aspect.rating', 'rating_id', string="Aspect Ratings",
        help="Optional per-aspect scores (e.g. 'Comfort: 4/5') the "
             "reviewer gave alongside the overall star rating.",
    )

    def _set_aspect_ratings(self, values):
        """Create rating.aspect.rating lines from a {aspect_id: value}
        mapping posted by the review composer.

        Silently ignores aspect ids that are not actually configured for
        the reviewed product's categories, or values outside 1-5, rather
        than failing the whole review submission over a stray/tampered
        payload - the overall review must never be lost because of a
        problem with an optional sub-score.
        """
        self.ensure_one()
        if not values or self.res_model != 'product.template' or not self.res_id:
            return
        Product = self.env['product.template'].sudo().browse(self.res_id)
        allowed_ids = set(Product._get_review_aspects().ids)
        if not allowed_ids:
            return
        vals_list = []
        seen = set()
        for aspect_id, value in dict(values).items():
            try:
                aspect_id = int(aspect_id)
                value = float(value)
            except (TypeError, ValueError):
                continue
            if aspect_id not in allowed_ids or aspect_id in seen:
                continue
            if value < 1 or value > 5:
                continue
            seen.add(aspect_id)
            vals_list.append({
                'aspect_id': aspect_id,
                'rating_id': self.id,
                'value': value,
            })
        if vals_list:
            self.env['rating.aspect.rating'].sudo().create(vals_list)

    def get_aspect_rating_data(self):
        """Lightweight serialisation for the portal frontend (aspect
        stars shown alongside the review, mirroring get_attachment_data)."""
        self.ensure_one()
        return [
            {'id': ar.aspect_id.id, 'name': ar.aspect_id.name, 'value': ar.value}
            for ar in self.aspect_rating_ids
        ]

    def get_attachment_data(self):
        """Lightweight serialisation for the portal frontend (thumbnails + lightbox)."""
        self.ensure_one()
        result = []
        for att in self.attachment_ids:
            mimetype = (att.mimetype or '').split(';')[0].strip().lower()
            is_image = mimetype.startswith('image/')
            is_video = mimetype.startswith('video/')
            result.append({
                'id': att.id,
                'name': att.name or '',
                'mimetype': mimetype,
                'is_image': is_image,
                'is_video': is_video,
                'url': '/web/content/%s?download=false' % att.id,
                'access_token': att.access_token or '',
            })
        return result
