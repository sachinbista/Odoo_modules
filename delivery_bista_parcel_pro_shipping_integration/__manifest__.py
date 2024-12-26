# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'Parcel Pro Shipping',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'company': 'Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'category': 'Point of Sale',
    'summary': """parcel pro shipping integration""",
    'description': """parcel pro shipping integration""",
    'depends': ['base','delivery', 'mail'],
    'data': [
            'security/ir.model.access.csv',
            'data/parcel_pro_data.xml',
            'views/delivery_carrier_view.xml',
            'views/sale_order_view.xml',
            'views/product_product_view.xml',
            'views/stock_picking_view.xml',
        ],
    'assets': {
        'web.assets_backend': [
            'delivery_bista_parcel_pro_shipping_integration/static/src/scss/tree_view.scss',

        ],

},
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,

}

