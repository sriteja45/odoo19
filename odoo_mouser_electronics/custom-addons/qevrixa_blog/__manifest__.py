{
    "name": "Qevrixa Blog",
    "version": "19.0.1.0.0",
    "summary": "Custom Blog for Qevrixa Electronics",
    "description": """
        Custom Blog Module for Qevrixa Electronics Website.
    """,
    "author": "Qevrixa Electronics",
    "website": "",
    "category": "Website",
    "license": "LGPL-3",
    "depends": [
        "web",
        "website",
        "website_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/blog_views.xml",
        "views/blog_review_views.xml",
        "views/blog_menu.xml",
        "views/blog_templates.xml",
        "views/blog_detail_template.xml",
        "views/website_menu.xml",
        "views/chat_widget.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "qevrixa_blog/static/src/css/blog.css",
        ],
        "web.assets_backend": [
            "qevrixa_blog/static/src/css/blog_admin_chat.css",
            "qevrixa_blog/static/src/js/blog_admin_chat.js",
            "qevrixa_blog/static/src/js/blog_chat.js",
            "qevrixa_blog/static/src/xml/blog_admin_chat.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}