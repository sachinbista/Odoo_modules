# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


{
    'name': 'Bista Purchase Delivery Order',
    'category': 'Sale order',
    'summary': 'Adding new fields',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ Adding new fields""",
    'depends': ['stock_account', 'purchase', 'base'],
    'data': [
        'views/purchase_delivery_order_view.xml'
    ],
    'installable': True,
    'application': True,
}
