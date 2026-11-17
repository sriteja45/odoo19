{
    "name": "Mouser Accounting Reports",
    "version": "19.0.1.0.0",
    "summary": "Financial Reports for Mouser Electronics",
    "category": "Accounting",
    "author": "Your Company",
    "license": "LGPL-3",

    "depends": [
        "account",
        "sale",
        "purchase",
        "stock",
        "product"
    ],

    "data": [

        "security/ir.model.access.csv",

        "views/profit_loss_views.xml",
        "views/balance_sheet_views.xml",
        "views/executive_summary_views.xml",

        "views/menu.xml",

    ],

    "installable": True,
    "application": True,
}