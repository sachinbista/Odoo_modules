# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Auto Email Sales Invoice',
    'version': '1.0',
    'category': 'sale',
    'license': 'LGPL-3',
    'description': '''
        This module will auto email invoice to the customer when it is creating from sales order using auto invoice 
        module if the auto email invoice field is checked in the sales order payment terms
    ''',
    'author': 'Omid Totakhel @ Bista Solutions',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': [
        'bista_auto_invoice'
    ],
    'data': [
        'views/payment_terms.xml',
        'views/account_move.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },

    'installable': True,
    'auto_install': False,
}
