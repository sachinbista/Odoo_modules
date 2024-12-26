# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bista SO Ship Together on MRP',
    'version': '15.0',
    'summary': 'This module creates a customer char field in sales order (Ship together) and inherits it to manufacturing orders',
    'description': """""",
    'category': 'sale',
    'depends': ['sale_stock', 'mrp'],
    "license": "LGPL-3",
    'data': [
        'views/sale_order.xml',
        'views/mrp_production.xml',
        'views/stock_picking.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {}
}
