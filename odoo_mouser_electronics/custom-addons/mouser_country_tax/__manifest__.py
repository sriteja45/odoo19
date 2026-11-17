{
    'name': 'Mouser Country Tax',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Apply taxes based on customer country',
    'author': 'Your Company',
    'depends': [
        'base',
        'sale',
        'account',
        'website_sale',
    ],
    'data': [
        'views/country_tax_views.xml',
        'views/menu_views.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': True,
}