# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'Pos Consignment',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'company': 'Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'category': 'Point of Sale',
    'summary': """check for consignment in pos side""",
    'description': """check for consignment in pos side""",
    'depends': ['point_of_sale','bista_consignment_report'],
    'data': [
            'views/pos_config_view.xml',
            'views/pos_order_line_view.xml',
        ],
    'assets': {
        'point_of_sale.assets': [
                'bista_pos_consignment/static/src/js/orderline_screen.js',
                'bista_pos_consignment/static/src/xml/orderline_screen_template.xml',

        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}

