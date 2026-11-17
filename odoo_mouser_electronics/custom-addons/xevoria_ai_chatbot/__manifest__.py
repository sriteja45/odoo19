{
    "name": "Xevoria AI ChatBot",
    "version": "19.0.1.0.0",
    "author": "Xevoria",
    "website": "https://xevoria.com",
    "license": "LGPL-3",

    "depends": [
        "mail",
        "im_livechat",
        "website_livechat",
    ],

    "data": [
    ],

    "assets": {

        "web.assets_backend": [

            "xevoria_ai_chatbot/static/src/js/composer_patch.js",
            "xevoria_ai_chatbot/static/src/js/composer_actions_patch.js",
            # "xevoria_ai_chatbot/static/src/scss/composer.scss",

        ],
    },

    "installable": True,
    "application": False,
}