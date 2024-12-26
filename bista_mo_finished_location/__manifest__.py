# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Manufacturing Finished Product Location',
    'version': '15.0.0',
    'category': 'Manufacturing',
    'license': 'LGPL-3',
    'description': '''
        Add Manufacturing Finished Product Location Based on Respective Bill of Material.
    ''',
    'author': 'Bista Solutions',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['mrp', 'bista_inter_company_enhancement', 'stock'],
    'data': [
        'views/mrp_bom_views.xml',
        'wizard/change_production_location_view.xml',
        'security/ir.model.access.csv',
        'views/production_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'views/pricelist_items.xml',
        'views/stock_backorder_confirmation_views.xml',
    ],
    'assets': {
        'web.assets_backend': [

        ],
    },

    'installable': True,
    'auto_install': False,
}
