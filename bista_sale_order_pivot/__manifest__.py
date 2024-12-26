# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


{
    'name': 'Bista Sale Order Pivot',
    'category': 'Sale order',
    'summary': 'Adding new fields',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ Adding new fields in pivot view of sale order """,
    'depends': ['sale', 'bista_inventory_report', 'product','account_followup', 'bista_order_sequences'],
    'data': [
        'views/sale_order_view.xml'
    ],
    'installable': True,
    'application': True,
}
