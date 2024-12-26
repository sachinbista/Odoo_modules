# -*- coding: utf-8 -*-
{
    'name': 'FDS: Multi Pricelist Report',
    'summary': """Allow to select multiple pricelist on Pricelist Report.""",
    'description': """Allow to select multiple pricelist on Pricelist Report.""",
    'category': 'Sale',
    'version': '16.0',
    'depends': [
        'product',
    ],
    'data': [
        'report/product_pricelist_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fds_multi_pricelist_report/static/src/js/product_pricelist_report.js',
            'fds_multi_pricelist_report/static/src/xml/pricelist_report.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
