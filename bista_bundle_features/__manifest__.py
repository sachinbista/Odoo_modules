# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bista Bundle Features',
    'category': 'Sales',
    'author': "Bista Solutions",
    'version': '16.0.1.0',
    'summary': "Bista Bundle Features",
    'description': """ Bista Bundle Features :
        - Disable quick create for m2o
        - Sticky header in List View and Kanban View
        - Added field in search view for smart search
        - Manage Chatter position
        - Made wizard size bigger
        - Made Screen size bigger
        - Line views of SO , PO , Stock , INV
     """,
    "license" : "OPL-1",
    'depends': ['sale_management','purchase','stock','account'],
    'data': [
        'security/security.xml',
        'views/all_in_one_sale.xml',
        'views/all_in_one_purchse.xml',
        'views/stock_operstion.xml',
        'views/account_invoice.xml',
        'views/ir_model_views.xml',
        'views/res_users_view.xml',
    ],

    "assets": {
        "web.assets_backend": [
            "/bista_bundle_features/static/src/scss/custom.scss",
            "/bista_bundle_features/static/src/js/form_chatter_position.js",
            "/bista_bundle_features/static/src/js/disable_quick_create.js",
        ],

    },

    'installable': True,
    'auto_install': False,
    'currency': "EUR",
    "uninstall_hook": "uninstall_hook",
}
