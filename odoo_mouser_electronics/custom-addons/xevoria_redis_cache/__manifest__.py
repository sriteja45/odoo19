{
    
    "name": "Xevoria Redis Cache",
    "summary": "Redis caching for Website Sale products",
    "version": "19.0.1.0.0",
    "author": "Xevoria",
    "website": "https://mouserelectronics.dealwallet.com/",
    "category": "Website",
    "license": "LGPL-3",

    "depends": [
        "base",
        "base_setup",
        "website_sale",
        "point_of_sale",
    ],

    "data": [
        "views/res_config_settings_views.xml",
    ],

    "installable": True,
    "application": False,
}