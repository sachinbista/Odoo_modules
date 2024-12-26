# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'POS Serial Number Validator',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'company': 'Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'category': 'Point of Sale',
    'summary': """Validate Serial number of a product by checking availability in stock""",
    'description': """Validate Serial number of a product by checking availability in stock""",
    'depends': ['point_of_sale'],
    'assets': {
        'web.assets_backend': [
            'bista_pos_traceability/static/src/js/*.*',
        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}

