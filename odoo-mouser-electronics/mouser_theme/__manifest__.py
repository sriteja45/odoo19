{
    'name': 'Mouser Theme',
    'version': '1.3.0',
    'summary': 'Custom homepage and manufacturers pages inspired by Mouser Electronics',
    'author': 'TSSS',
    'category': 'Website',
    'depends': ['website', 'website_sale'],
    'data': ['security/ir.model.access.csv', 'data/mouser_api_config.xml', 'data/manufacturer_data.xml', 'data/new_manufacturer_records.xml', 'views/manufacturer_views.xml', 'views/manufacturer_templates.xml', 'views/homepage_template.xml', 'views/automation_expo_template.xml', 'views/local_sites_template.xml', 'views/home_promo_templates.xml', 'views/contact_template.xml', 'views/feedback_template.xml', 'views/services_tools.xml', 'views/gst_bill_format_template.xml', 'views/methods_of_payment_template.xml', 'views/credit_privacy_templates.xml', 'views/ecia_template.xml', 'views/accessibility_template.xml', 'views/electronic_components_template.xml', 'views/semiconductors_category_template.xml', 'views/newest_products_template.xml'],
    'assets': {'web.assets_frontend': ['mouser_theme/static/src/css/mouser_style.css', 'mouser_theme/static/src/js/mouser_main.js']},
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
