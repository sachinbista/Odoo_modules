# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bista FDS Margin',
    'category': 'Sale order',
    'summary': 'FDS Margin',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ FDS Margin """,
    'depends': ['sale', 'base','sale_margin'],
    'data': [
        'views/account_move_view.xml',
        'views/product_template_view.xml',

    ],
    'installable': True,
    'application': True,
}
