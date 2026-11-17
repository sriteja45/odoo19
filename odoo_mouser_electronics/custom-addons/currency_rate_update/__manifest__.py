{
    "name": "Currency Rate Update",
    "version": "19.0.1.0.0",
    "summary": "Automatically update currency exchange rates from an online API",
    "description": """
        Automatically fetches live currency exchange rates
        and updates Odoo currency rates using a scheduled cron job.
    """,
    "category": "Accounting",
    "author": "Your Company",
    "website": "https://yourcompany.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/currency_rate_views.xml",
        "data/currency_rate_cron.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}