# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Sale Order Addresses',
    'version': '1.0',
    'category': 'CRM',
    'license': 'LGPL-3',
    'description': '''
        This module enables users to create partner from sales order along with address.
    ''',
    'author': 'Omid Totakhel @ Bista Solutions',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['base', 'sale'],
    'data': [
        'views/sale_order.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
}
