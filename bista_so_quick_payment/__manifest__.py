# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bista Sales Order Quick Payment',
    'version': '15.0',
    'summary': 'This module lets users to generate inoice and register payment from the sales order view',
    'description': """""",
    'category': 'crm',
    'depends': ['sale', 'account'],
    "license": "LGPL-3",
    'data': [
        'views/sale_advance_payment_inv.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {}
}
