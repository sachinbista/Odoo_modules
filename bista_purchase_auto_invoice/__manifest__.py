# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Purchase Auto-Invoice',
    'version': '17.0.0.1',
    'summary': 'Create Auto Invoice From Delivery Order',
    'description': """
Sale Order - Create Automatic Invoice while validate Delivery Order
====================================================================
This module allows you to create invoice automatically once delivery order
is processed, invoice will take only those product which has invoice policy
as a Delivered Quantity
    """,
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    'depends': ['sale_stock', 'sale_management'],
    'category': 'Accounting',
    'data': [
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3'
}
