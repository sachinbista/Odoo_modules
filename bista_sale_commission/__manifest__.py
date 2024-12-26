# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


{
    'name': 'Bista Sale Commission',
    'category': 'Sale order',
    'summary': 'Sale Commission',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ Sale commission """,
    'depends': ['sale', 'base', 'account', 'bista_auto_invoice'],
    'data': [
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',

    ],
    'installable': True,
    'application': True,
}
