# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """ EXTENSION of res.config.settings, the same transient model
    website_sale itself extends for its own eCommerce settings. We reuse
    the standard `config_parameter` field attribute so persistence,
    get/set, and the Settings screen's own save mechanism are all the
    stock Odoo ones - no custom settings storage is introduced.
    """
    _inherit = 'res.config.settings'

    review_auto_approve = fields.Boolean(
        string="Auto-publish reviews",
        config_parameter='website_sale_review_extended.auto_approve_reviews',
        default=True,
        help="If disabled, new customer reviews stay hidden from the "
             "product page until a shop manager approves them.",
    )
    review_auto_request_enabled = fields.Boolean(
        string="Automatically request reviews after delivery",
        config_parameter='website_sale_review_extended.auto_request_enabled',
        default=False,
        help="Sends the 'Rate your purchase' email automatically once a "
             "sales order line has been delivered.",
    )
    review_request_delay_days = fields.Integer(
        string="Days after delivery to request a review",
        config_parameter='website_sale_review_extended.request_delay_days',
        default=7,
    )

    # ------------------------------------------------------------------
    # Anti-spam (Phase 5) - tuning for rating.rating._wsre_check_review_spam()
    # ------------------------------------------------------------------
    review_spam_rate_limit_count = fields.Integer(
        string="Max reviews per window",
        config_parameter='website_sale_review_extended.spam_rate_limit_count',
        default=5,
        help="A partner (or IP address, for cases where no partner can be "
             "matched) posting this many reviews within the time window "
             "below has their next submission rejected outright.",
    )
    review_spam_rate_limit_window_minutes = fields.Integer(
        string="Rate-limit window (minutes)",
        config_parameter='website_sale_review_extended.spam_rate_limit_window_minutes',
        default=60,
    )
    review_spam_duplicate_check_enabled = fields.Boolean(
        string="Flag duplicate review text",
        config_parameter='website_sale_review_extended.spam_duplicate_check_enabled',
        default=True,
        help="When a new review's text hashes the same as another recent "
             "review (30-day lookback), don't reject it - force it back "
             "to 'Pending Approval' so a moderator decides, even if "
             "auto-publish is on.",
    )
