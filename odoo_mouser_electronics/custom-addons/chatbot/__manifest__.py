{
    'name': 'Website Chatbot',

    'version': '1.0',

    'category': 'Website',

    'summary': 'Frontend Chatbot for Mouser Electronics',

    'author': 'varshitha',

    'license': 'LGPL-3',

    'depends': [
        'website',
        'web',
    ],

    'data': [
        'views/chatbot_template.xml',
    ],

    'assets': {

        'web.assets_frontend': [

            'chatbot/static/src/css/chatbot.css',

            'chatbot/static/src/js/chatbot.js',

        ],

    },

    'installable': True,

    'application': True,

    'auto_install': False,
}