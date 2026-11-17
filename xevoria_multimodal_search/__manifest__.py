# -*- coding: utf-8 -*-
{
    'name': 'Xevoria Multimodal Vector Search (EmbeddingGemma 2)',
    'version': '19.0.1.0.2',
    'category': 'Website/eCommerce/AI',
    'summary': 'Multimodal AI product search for eCommerce using Google EmbeddingGemma 2 unified text, image, and video vectors',
    'description': """
Xevoria Multimodal Vector Search (EmbeddingGemma 2)
===================================================
Enables visual and semantic vector search across eCommerce products in Odoo 19 using Google's EmbeddingGemma 2.

Key Features:
* Unified 768-dimensional multimodal vector space mapping text, images, and videos natively
* Optimized 440M parameter vision-text configuration (omitting audio encoder & using bfloat16 for low RAM usage)
* Visual Image & Video Search: Upload product photo or video clip to find matching parts and products
* Instruction-aware task prefixes (task: search result | query: for searches, title: ... | text: ... for catalog items)
* Matryoshka Representation Learning (MRL) dimension scaling (768d, 512d, 256d)
* In-database vector storage with fast cosine similarity retrieval (PgVector or zero-dependency in-DB fallback)
* Pure CSS styling (does not require external sassc binary on Windows)
    """,
    'author': 'Dealwallet / Xevoria',
    'website': 'https://dealwallet.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'website',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/multimodal_embedding_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/website_search_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'xevoria_multimodal_search/static/src/css/multimodal_search.css',
            'xevoria_multimodal_search/static/src/js/multimodal_search.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
