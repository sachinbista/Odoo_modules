# -*- coding: utf-8 -*-
##############################################################################
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
##############################################################################
{
    'name': 'Bista MRP Cost',
    'version': '15.0.0',
    'category': 'sale',
    'license': 'LGPL-3',
    'description': '''
        Apply Labor and overhead cost to finished product
        ''',
    'author': 'Omid Totakhel @ Bista Solutions',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': [
        'base', "mrp", 'stock_account', 'mrp_account_enterprise', 'web'
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/cost_structure_report.xml',
        'views/mrp_bom_cost.xml',
        'views/account_move_line.xml',
        'views/ir_config_settings.xml',
    ],
    "assets": {
        "web.assets_common": [
            'bista_mrp_cost/static/src/css/style.scss',
        ],
        'web.assets_backend': [
            'bista_mrp_cost/static/src/js/many2one_field.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}
