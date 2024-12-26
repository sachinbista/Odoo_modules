# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Unreserve Stock Move',
    'version': '15.0.0',
    'category': 'accounting',
    'license': 'LGPL-3',
    'description': '''Unreserve stock move from stock picking line''',
    'author': 'Omid Totakhel @ Bista Solutions',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': [
        'base',  'stock'
    ],
    'data': [
        'views/stock_move.xml',

    ],
    'installable': True,
    'auto_install': False,
}
