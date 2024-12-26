# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Special Order',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'tools',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Order Enhancement',
    'description': """ This module is allowed to set an order as special and that can not be returned.
   
    """,
    'depends': [
        'sale','website_sale','point_of_sale','pos_orders_all','base'
    ],
    'data': [
        'security/res_groups.xml',
        'views/sale_views.xml',
        'views/stock_views.xml',
        'views/pos_order_view.xml',
        'views/res_config_setting.xml',

    ],
    'assets': {
            'point_of_sale.assets': [
                'bista_special_order/static/src/js/orderline_screen.js',
                'bista_special_order/static/src/js/TicketScreen.js',
                'bista_special_order/static/src/js/create_sale.js',
                'bista_special_order/static/src/xml/pos_special_order_template.xml',
                'bista_special_order/static/src/xml/orderline_details.xml',
                'bista_special_order/static/src/xml/return_order.xml',
                'bista_special_order/static/src/xml/order_details_template.xml',
                'bista_special_order/static/src/xml/sale_order.xml',
                ],
        },
    'installable': True,
    'application': True,
}
