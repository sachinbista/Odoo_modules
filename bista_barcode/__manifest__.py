# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd.
# Copyright (C) 2020 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Barcode',
    'version': '15.0.0.1.1',
    'summary': 'Barcode enhancement',
    'description': """""",
    'category': 'barcode',
    'license': 'LGPL-3',
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'depends': ['stock_barcode', 'sale', 'product', 'stock_barcode'],
    'data': [
        'views/stock_lot.xml',
        'views/stock_picking_type.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bista_barcode/static/src/js/barcode_picking_model.js',
            'bista_barcode/static/src/js/barcode_quant.js',
            'bista_barcode/static/src/js/barcode_line.js',
            'bista_barcode/static/src/js/main.js',
            'bista_barcode/static/src/template/stock_barcode.xml',

        ],

    },
    'installable': True,
}
