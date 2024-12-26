# -*- coding: utf-8 -*-

{
    "name": "Inventory Extensions",
    "version": "17.0.1.0.0",
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    "license": "LGPL-3",
    "category": "",
    "depends": ["base", "stock", "stock_barcode",
                'stock_barcode_picking_batch', 'stock_delivery'],
    "data": [
        'security/ir.model.access.csv',
        'views/stock_quant_packaging_views.xml',
        'views/stock_picking_batch_view.xml',
        'wizard/choose_delivery_package_view.xml',
        'report/report_delivery_inherit.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'inventory_extension/static/src/js/barcode_picking_model.js',
        ],
    }
}
