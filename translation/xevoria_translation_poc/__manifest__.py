{'name': 'Xevoria Translation POC',
 'version': '19.0.1.0.44',
 'category': 'Website/eCommerce',
 'summary': 'POC for dynamic product name and description translations on website',
 'description': '\n'
                'POC module to manage dynamic product translations for Odoo 19.\n'
                "It stores translation rows per product/language and applies them to Odoo's native translatable "
                'product fields.\n'
                '\n',
 'depends': ['base', 'product', 'website', 'website_sale'],
 'external_dependencies': {'python': ['requests', 'lxml']},
 'data': ['security/ir.model.access.csv',
          'data/translation_queue_cron.xml',
          'views/product_translation_views.xml',
          'views/product_template_views.xml',
          'views/product_website_sale_description_views.xml',
          'views/res_config_settings_views.xml',
          'views/bulk_translation_wizard_views.xml',
          'views/translation_queue_views.xml',
          'views/translation_memory_views.xml',
          'views/translation_dashboard_views.xml'],
 'installable': True,
 'application': False,
 'license': 'LGPL-3'}