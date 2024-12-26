# -*- coding: utf-8 -*-
# Part of Bistasolutions. See LICENSE file for full copyright and licensing details.

{
    "name": "Bista POS Tax Enhancement",
    "version": "16.0.1.0.0",
    "category": "Point of Sale",
    'summary': 'POS Tax calculation',
    "description": """
    
  Bista POS Tax : Tax calculation based on Customer or Product Tax type
    
    """,
    "author": "Bistasolutions",
    "website": "https://www.bistasolutions.com",
    "currency": 'EUR',
    "depends": ['point_of_sale','pos_orders_all'],
    "data": [
        'views/product_template_view.xml',
    ],

    "auto_install": False,
    'license': 'OPL-1',
    "installable": True,
    'assets': {
        'point_of_sale.assets': [
            'bista_pos_tax_enhancement/static/src/js/Misc/Orderline.js',
        ],
    },
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
