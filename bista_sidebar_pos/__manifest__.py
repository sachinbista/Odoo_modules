# -*- coding: utf-8 -*-
# Part of Bistasolutions. See LICENSE file for full copyright and licensing details.

{
    "name": "Bista Sidebar POS",
    "version": "16.0.1.0.0",
    "category": "Point of Sale",
    'summary': 'Bista Sidebar POS used to hide show button based on user configuration',
    "description": """
    
  Bista Sidebar POS : used to hide show button based on user configuration
    
    """,
    "author": "Bistasolutions",
    "website": "https://www.bistasolutions.com",
    "currency": 'EUR',
    "depends": ['point_of_sale', 'pos_hr', 'pos_all_in_one'],
    "data": [
        'views/custom_pos_disable_view.xml',
    ],

    "auto_install": False,
    'license': 'OPL-1',
    "installable": True,
    'assets': {
        'point_of_sale.assets': [
            'bista_sidebar_pos/static/src/css/sidebar.css',
            'bista_sidebar_pos/static/src/xml/pos_disable.xml',
        ],
    },
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
