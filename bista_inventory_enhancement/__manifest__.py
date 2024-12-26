# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Inventory Enhancement',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'tools',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Inventory Enhancement',
    'description': """ This module is allowed to find the Date according to inventory adjustment for that specific product
   
    """,
    'depends': [
        'base', 'sync_inventory_adjustment', 'web_tour', 'web_mobile','mail','stock_barcode','web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/product_template_view.xml',
        'views/inventory_view.xml',
        'views/res_users_view.xml',
        'wizard/pin_message_wizard.xml',
        'reports/report_stock_inventory.xml',
        'data/stock_inventory_adjustment.xml'
    ],
    "assets": {
            'web.assets_qweb': [
                'bista_inventory_enhancement/static/src/**/*.xml',
            ],  
            'web.assets_backend': [
                'bista_inventory_enhancement/static/src/**/*.js',
                'bista_inventory_enhancement/static/src/**/*.xml',
                'bista_inventory_enhancement/static/src/**/*.scss',
            ],
        },
    'installable': True,
    'application': True,
}
