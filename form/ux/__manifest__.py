{
    'name': 'UX Form',
    'version': '1.0',
    'summary': 'Custom Feedback Web Form',
    'category': 'Website',
    'author': 'TSSS',
    'license': 'LGPL-3',
    'depends': ['base', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/feedback_templates.xml',
    ],
    'installable': True,
    'application': True,
}
