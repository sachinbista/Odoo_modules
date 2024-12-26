# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bista Account Move',
    'version': '15.0',
    'summary': 'This module prevent bugs from making changes to the account move line partner',
    'description': """""",
    'category': 'purchase',
    'depends': ['purchase', 'purchase'],
    "license": "LGPL-3",
    'data': [
        'views/account_move.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {}
}
