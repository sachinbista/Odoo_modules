# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bista FDS CRM',
    'version': '15.0',
    'summary': 'Custom module for FDS Report',
    'description': """""",
    'category': 'crm',
    'depends': ['sale_stock', 'delivery'],
    "license": "LGPL-3",
    'data': [
        'views/sale_order.xml',
        'views/stock_warehouse.xml',
        'views/stock_picking.xml',
        'views/account_move.xml',
        'views/purchase_order.xml',
        'views/mrp_production.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {}
}
