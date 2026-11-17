# -*- coding: utf-8 -*-
{
    'name': "Website Sale Review Extended (Verified Purchase, Moderation, Voting, Auto-Request)",
    'summary': "Extends Odoo's native eCommerce review system instead of replacing it: "
               "verified-purchase badges, review moderation, helpful/unhelpful voting, "
               "automated review-request emails, rich media (photos/videos) on reviews, variant-attributed reviews, "
               "product Q&A, review search & quick filters, per-aspect (sub-)ratings, "
               "Review/AggregateRating JSON-LD, verified-purchase/recency-weighted scoring, review anti-spam.",
    'description': """
Existing Feature Reuse & Extension
===================================
This module does NOT reimplement Odoo's review system. It extends the stock
models/views/templates that already ship in ``rating``, ``portal_rating`` and
``website_sale`` via standard Odoo inheritance (``_inherit`` / ``t-inherit``),
so every original behaviour, security rule and upgrade path is preserved.

What is reused as-is (no changes):
    * rating.rating              (core review record)
    * mail.message / mail.thread (review submission, chatter, comments)
    * portal_rating composer widget (star picker, textarea, attachment upload)
    * product.template rating.mixin (average rating / review count on products)
    * sale.order / sale.order.line (source of truth for "did this partner buy this?")

What is added by EXTENSION (new fields/methods on existing models, calling super()):
    * rating.rating: is_verified_purchase, moderation_status, is_anonymous,
      helpful_count, unhelpful_count, attachment_ids (review media),
      product_id / product_variant_display (variant attribution),
      aspect_rating_ids (per-aspect scores)
    * product.template: _rating_domain() extended to also require moderation_status
      = 'approved' (falls back to the exact stock behaviour when moderation is
      switched off, so nothing breaks for existing installs); search_reviews()
      and get_review_aspect_averages() reuse that same domain for search/filters
    * product.public.category: aspect_ids (inverse of rating.aspect.public_category_ids)
      so aspects can be configured per website category
    * mail.message: _portal_message_format() extended to expose the new fields
      to the existing frontend widget
    * mail.thread: message_post() extended to accept review_aspect_ratings
      alongside the existing review_attachment_ids / review_product_id kwargs
    * sale.order / sale.order.line: review-request tracking fields + one button,
      added to the existing form view via view inheritance (no new screens)
    * product.template: rating_weighted_avg / rating_weighted_count (NEW,
      additive fields - core rating_avg/rating_count untouched) + get_review_jsonld();
      website_sale.product / product_title / products_item templates extended
      (t-inherit) to display the weighted score and publish JSON-LD
    * rating.rating: submission_ip, feedback_hash, is_flagged_duplicate +
      create() extended with a rate-limit / duplicate-content anti-spam gate

What is added as NEW supporting objects (justified because no equivalent exists
in core to extend):
    * rating.vote          - one row per (review, partner) helpful/unhelpful vote
    * product.question / product.answer - product Q&A (no core equivalent)
    * rating.aspect / rating.aspect.rating - configurable sub-ratings
      (e.g. "Comfort: 4/5") per product review, since core only ever
      stores one overall score per rating.rating
    * ir.cron + mail.template - review-request automation + new-question alerts
    """,
    'version': '19.0.1.5.0',
    'category': 'Website/Website',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': [
        'website_sale',
        'portal_rating',
        'rating',
        'sale',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/rating_rating_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_question_views.xml',
        'views/product_qa_templates.xml',
        'views/rating_aspect_views.xml',
        'views/product_public_category_views.xml',
        'views/product_seo_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_review_extended/static/src/js/review_message_patch.js',
            'website_sale_review_extended/static/src/js/review_composer_patch.js',
            'website_sale_review_extended/static/src/js/review_variant_filter.js',
            'website_sale_review_extended/static/src/js/product_qa.js',
            'website_sale_review_extended/static/src/js/review_search_filter.js',
            'website_sale_review_extended/static/src/xml/review_message_patch.xml',
            'website_sale_review_extended/static/src/xml/review_composer_patch.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
