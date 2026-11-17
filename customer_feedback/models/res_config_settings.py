from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # NOTE: Integer/Float fields deliberately do NOT use the config_parameter=
    # attribute here. Odoo's built-in res.config.settings.set_values() does:
    #     value = repr(value) if value else False
    # for every integer/float config field, which treats 0 as falsy, converts
    # it to False, and set_param(key, False) deletes the stored parameter.
    # The next page load then falls back to the field's Python default,
    # silently reverting any "0" the user entered (e.g. Waiting Period).
    # We handle get/set manually below (int(...) with a real default via
    # get_param's own default arg) so 0 is stored and read back correctly.
    _INT_CONFIG_FIELDS = {
        'feedback_waiting_days': ('customer_feedback.waiting_days', 3),
        'feedback_expiry_days': ('customer_feedback.expiry_days', 15),
        'feedback_reminder_days': ('customer_feedback.reminder_days', 4),
        'feedback_max_email_retries': ('customer_feedback.max_email_retries', 3),
        'feedback_review_min_length': ('customer_feedback.review_min_length', 10),
        'feedback_review_max_length': ('customer_feedback.review_max_length', 2000),
        # Step 8 — media limits
        'feedback_media_max_images': ('customer_feedback.media_max_images', 5),
        'feedback_media_max_videos': ('customer_feedback.media_max_videos', 2),
    }
    _FLOAT_CONFIG_FIELDS = {
        'feedback_media_max_size_mb': ('customer_feedback.media_max_size_mb', 10.0),
    }

    feedback_waiting_days = fields.Integer(string='Waiting Period (days)', default=3)
    feedback_expiry_days = fields.Integer(string='Link Expiry (days)', default=15)
    feedback_reminder_days = fields.Integer(string='Reminder Delay (days)', default=4)
    feedback_max_email_retries = fields.Integer(string='Max Email Retries', default=3)
    feedback_admin_notification_email = fields.Char(
        string='Admin Notification Email',
        config_parameter='customer_feedback.admin_notification_email')
    # Boolean config_parameter + default=True is broken in Odoo: set_param(False)
    # deletes the key, so the next load falls back to default=True and the
    # checkbox re-checks itself. Handle get/set manually with string 'True'/'False'.
    feedback_moderation_enabled = fields.Boolean(
        string='Enable Review Moderation')
    feedback_customer_name_display = fields.Selection([
        ('full', 'Full Name'),
        ('masked', 'Masked (e.g. "John D.")'),
        ('anonymous', 'Anonymous Customer'),
    ], string='Customer Name Display', default='full', required=True,
        config_parameter='customer_feedback.anonymous_display')
    feedback_allow_review_edit = fields.Boolean(
        string='Allow Customers to Edit Reviews', default=False,
        config_parameter='customer_feedback.allow_review_edit')
    feedback_review_min_length = fields.Integer(string='Minimum Review Length', default=10)
    feedback_review_max_length = fields.Integer(string='Maximum Review Length', default=2000)
    # Rating ownership mode: runtime value lives in ir.config_parameter.
    # Default is shared (native ratings continue to count). Exclusive is an
    # explicit business-approved exception that excludes unowned product
    # ratings from native aggregates.
    feedback_rating_ownership = fields.Selection(
        [
            ('shared', 'Shared / Additive (default)'),
            ('exclusive', 'Exclusive (verified reviews only)'),
        ],
        string='Product Rating Ownership',
        default='shared',
        required=True,
        help='Shared (default): existing native Odoo product ratings and '
             'approved verified reviews both contribute to rating_avg / '
             'rating_count. Exclusive: only approved verified reviews from '
             'this module count; unowned native product ratings are excluded '
             'from aggregates. Exclusive mode changes the behaviour of '
             'existing Odoo rating data and must only be enabled with '
             'explicit business approval.',
    )


    # Step 8 — Review photos & videos
    feedback_media_enabled = fields.Boolean(
        string='Allow Review Photos & Videos',
        help='Let customers attach images and short videos when submitting a review. '
             'Files are stored as ir.attachment (filestore by default; S3/object '
             'storage works when configured on the Odoo instance).',
    )
    feedback_media_max_images = fields.Integer(
        string='Max Images per Review', default=5,
    )
    feedback_media_max_videos = fields.Integer(
        string='Max Videos per Review', default=2,
    )
    feedback_media_max_size_mb = fields.Float(
        string='Max File Size (MB)', default=10.0,
        help='Maximum size per uploaded file in megabytes.',
    )
    feedback_media_moderation_separate = fields.Boolean(
        string='Separate Media Moderation',
        help='When enabled, each photo/video has its own pending/approved/rejected '
             'status independent of the parent review. When disabled (default), '
             'media is published or hidden together with the review.',
    )

    # Website display — product-page auto-injection (Step 5)
    # Default True preserves current behaviour. When False, the reviews
    # section is not auto-injected on product pages; merchants can still
    # drop the snippet manually via the Website Builder.
    feedback_show_on_product_page = fields.Boolean(
        string='Show Reviews on Product Pages',
        help='Global switch (default ON): auto-inject Customer Reviews on product '
             'pages. When OFF, nothing is auto-injected; place the snippet manually '
             'via Website Builder where needed. Use snippet option '
             '"Hide entire block on frontend" for per-page hide.',
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        res['feedback_moderation_enabled'] = (
            icp.get_param('customer_feedback.moderation_enabled', 'True') == 'True'
        )
        ownership = icp.get_param('customer_feedback.rating_ownership', 'shared')
        if ownership not in ('shared', 'exclusive'):
            ownership = 'shared'
        res['feedback_rating_ownership'] = ownership
        res['feedback_media_enabled'] = (
            icp.get_param('customer_feedback.media_enabled', 'True') == 'True'
        )
        res['feedback_media_moderation_separate'] = (
            icp.get_param('customer_feedback.media_moderation_separate', 'False') == 'True'
        )
        res['feedback_show_on_product_page'] = (
            icp.get_param('customer_feedback.show_on_product_page', 'True') == 'True'
        )
        for field_name, (param_key, default) in self._INT_CONFIG_FIELDS.items():
            res[field_name] = int(icp.get_param(param_key, default))
        for field_name, (param_key, default) in self._FLOAT_CONFIG_FIELDS.items():
            res[field_name] = float(icp.get_param(param_key, default))
        return res

    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param(
            'customer_feedback.moderation_enabled',
            'True' if self.feedback_moderation_enabled else 'False',
        )
        ownership = self.feedback_rating_ownership or 'shared'
        if ownership not in ('shared', 'exclusive'):
            ownership = 'shared'
        icp.set_param('customer_feedback.rating_ownership', ownership)
        icp.set_param(
            'customer_feedback.media_enabled',
            'True' if self.feedback_media_enabled else 'False',
        )
        icp.set_param(
            'customer_feedback.media_moderation_separate',
            'True' if self.feedback_media_moderation_separate else 'False',
        )
        icp.set_param(
            'customer_feedback.show_on_product_page',
            'True' if self.feedback_show_on_product_page else 'False',
        )
        for field_name, (param_key, _default) in self._INT_CONFIG_FIELDS.items():
            icp.set_param(param_key, str(self[field_name]))
        for field_name, (param_key, _default) in self._FLOAT_CONFIG_FIELDS.items():
            icp.set_param(param_key, str(self[field_name]))
