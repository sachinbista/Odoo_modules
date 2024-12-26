# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bista Proforma Features',
    'category': 'Sales',
    'author': "Bista Solutions",
    'version': '16.0.1.0',
    'summary': "Bista Proforma Features",
    'description': """ Bista Proforma Features :
        - Added Proforma state in Sale order
     """,
    "license" : "OPL-1",
    'depends': ['sale','bista_go_flow'],
    'data': [
        'views/sale_order_view.xml',
    ],

    "assets": {
    },

    'installable': True,
    'auto_install': False,
}
