{
    'name': 'Customer Feedback, Ratings & Reviews',
    'version': '19.0.2.32.0',
    'category': 'Sales/Sales',
    'summary': 'Verified-purchase ratings & reviews after delivery — extends native Odoo ratings',
    'description': """
Customer Feedback, Ratings & Reviews (Odoo 19 Community)
========================================================

Architecturally integrated with native rating.rating (Shared / Additive by default).

SINGLE SUBMISSION PATH (Step 1 — see doc/STEP1_NATIVE_OVERRIDE.md):
  Delivered order → feedback.request (token) → feedback.review → moderation
  → rating.rating (consumed when approved) → product.rating_avg / rating_count

Native free-form product reviews (website_sale.product_comment) are disabled.
Native Odoo remains the source of truth for:
- average rating (rating_avg)
- rating count (rating_count)
- product-page star display
- rating infrastructure (_rating_get_repartition)

This module extends native Odoo only where the verified-purchase business requirement is not satisfied by the standard feature:
- Automatic post-delivery feedback invitations (token links, no login)
- Configurable waiting period, link expiry, reminder emails
- Verified-purchase flag and badge
- Full moderation workflow (Pending / Approved / Rejected / Hidden)
- Review title
- Helpful / Not Helpful voting
- Sort & filter on the product page
- Customer portal "My Reviews" history
- Dashboard, PDF/Excel reports, REST API
- Retry / resend invitation tooling
- Review photos & videos (ir.attachment storage, optional separate media moderation)

On approve, each feedback.review creates/updates a corresponding rating.rating
so native averages and product-page widgets stay correct.

Rating ownership (default: shared / additive):
- Existing native product ratings continue to contribute to rating_avg /
  rating_count alongside approved verified reviews.
- Exclusive mode is an optional, explicit admin/migration-only exception that excludes unowned
  product ratings from aggregates; enable only with business approval.
- Historical ratings are never mass-reactivated when using shared mode.
- Ratings on unrelated models are never modified.

Star distribution uses native _rating_get_repartition() (no stored histogram).
Review text lives only on feedback.review (not duplicated into rating.feedback).
""",

    'author': 'TSSS',
    'license': 'LGPL-3',
    'depends': [
        'base_setup',
        'sale_management',
        'stock',
        'mail',
        'portal',
        'website',
        'website_sale',
        'rating',
    ],
    'data': [
        'security/feedback_security.xml',
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        'data/ir_exports.xml',
        'report/feedback_report.xml',
        'views/feedback_request_views.xml',
        'views/feedback_review_pivot.xml',
        'views/feedback_review_graph.xml',
        'views/feedback_review_views.xml',
        'views/feedback_report_views.xml',
        'views/feedback_report_wizard_views.xml',
        'views/feedback_resend_email_wizard_views.xml',
        'views/feedback_dashboard.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/portal_templates.xml',
        'views/snippets/s_feedback_reviews.xml',
        'views/website_templates.xml',
        'views/feedback_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'customer_feedback/static/src/css/feedback_reviews.css',
            'customer_feedback/static/src/interactions/feedback_review_vote.js',
        ],
        'website.website_builder_assets': [
            'customer_feedback/static/src/builder/plugins/feedback_reviews_option_plugin.js',
            'customer_feedback/static/src/builder/plugins/feedback_reviews_option.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
