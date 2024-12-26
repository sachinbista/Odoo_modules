# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "Bista Royalty Report",
    "version": "16.0",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": ['base', 'product', 'sale', 'commission', 'bista_sale_dropship', 'account', 'bista_go_flow'],
    "category": "Sale",
    "data": [
        "security/royalty_security.xml",
        'data/royalty_report.xml',
        'data/menu_item_data.xml',
        'security/ir.model.access.csv',
        'views/account_report_view.xml',
        'views/report_filter_view.xml',
        'views/report_menu_action.xml',
        'views/royalty_view.xml',
        'views/product_template.xml',
        'views/res_partner_view.xml',
        'views/product_royalty_list_view.xml',
        'views/account_move_view.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bista_royalty_report/static/src/js/account_reports.js',
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
