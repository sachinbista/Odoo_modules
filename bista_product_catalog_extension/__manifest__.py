# -*- coding: utf-8 -*-
{
    'name': "Bista Product Catalog Extension",
    'summary': """roduct Catalog Extension""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': 'Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['web', 'base', 'sale', 'product'],
    'data': [
        'views/product_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bista_product_catalog_extension/static/src/xml/product_catalog.xml',
            'bista_product_catalog_extension/static/src/js/product_catalog.js',
        ],
    },
    'installable': True,
    'application': True,
}
