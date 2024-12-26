# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Sales History Data',
    'version': '14.0.1',
    'sequence': 1,
    'category': 'Sales',
    'summary': 'Store and view old history data.',
    'description': """This module helps to store and view old history data.""",
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    'depends': ['base', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        # 'views/sale_history_data_view.xml',
        'views/sale_history_view.xml',
        # 'views/sale_history_line_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
