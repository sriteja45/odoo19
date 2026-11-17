{
    "name": "Xevoria Currency Rate Update",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Automatic Currency Rate Update using Exchange Rate API",
    "description": """
Automatically fetches live exchange rates
and updates Odoo currencies.
    """,
    "author": "Xevoria",
    "website": "https://www.xevoria.com",
    "license": "LGPL-3",

    "depends": [
        "account",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/currency_rate_update_views.xml",
        "data/currency_rate_cron.xml",
    ],

    "installable": True,
    "application": True,
}