{
    "name": "Mouser Order Tracking",
    "version": "19.0.1.0.0",
    "summary": "Amazon Style Order Tracking",
    "author": "Varshitha",
    "category": "Website",
    "license": "LGPL-3",

    "depends": [
        "base",
        "web",
        "sale",
        "sale_management",
        "portal",
        "website",
        "website_sale",
    ],

    "data": [
        "security/security.xml",
        # "security/ir.model.access.csv",

        
        "views/sale_order_views.xml",
        "views/my_orders.xml",
        "views/tracking_templates.xml",
    ],

    "assets": {
        "web.assets_frontend": [
            "mouser_order_tracking/static/src/css/tracking.css",
        ],
    },

    "installable": True,
    "application": False,
    "auto_install": False,
}