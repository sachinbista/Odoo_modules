# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Zpl Labels',
    'version': '15.0.0',
    'category': 'sale',
    'license': 'LGPL-3',
    'description': '''============================''',
    'author': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['base', 'stock', "web"],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'report/report_stock_production_lot.xml',
        'report/report_stock_location.xml',
        'report/report_stock_picking.xml',
        'report/report_stock_quant.xml',
        'report/report_product_template.xml',
        'report/action_report_picking_type_label.xml',
        'views/zpl_label.xml',
        'views/print_wizard.xml',
        'views/stock_production_lot.xml',
        'views/stock_location.xml',
        'views/stock_quant.xml',

    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'bista_zpl_labels/static/src/scss/*.scss',
        ],
    },
    'external_dependencies': {
        'python': ['zebrafy'],
    },
  #  'post_init_hook': '_generate_stock_barcode_action_pdf',
}
