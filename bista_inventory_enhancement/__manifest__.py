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
        'base', 'sync_inventory_adjustment', 'mail'
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/product_template_view.xml',
        'views/inventory_view.xml',
        'reports/report_stock_inventory.xml',
    ],

    'installable': True,
    'application': True,
}
