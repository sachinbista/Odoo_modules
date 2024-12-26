# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Go Flow",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Mansoor Bagwala",
    'website': "https://www.bistasolutions.com",

    'category': 'API Integeration',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'product',
                'delivery',
                # 'crm',
                'mail',
                'stock',
                'sale_management',
                'sign',
                'spring_systems_integration',
                'account',
                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/access_app_security.xml',
        'wizard/goflow_import_export_opt_view.xml',
        # 'wizard/open_goflow_split_order_wiz.xml',
        'wizard/goflow_hold_order_wiz.xml',
        'views/sign_request_document.xml',
        'views/inherit_res_config_setting_view.xml',
        'views/goflow_configuration_views.xml',
        'views/goflow_common_log_book.xml',
        'views/goflow_order.xml',
        'views/goflow_vendor_view.xml',
        'views/goflow_warehouse_views.xml',
        'views/goflow_channel_views.xml',
        'views/goflow_error_log_view.xml',
        'views/goflow_purchase_views.xml',
        'views/inherit_sale_order_view.xml',
        'views/stock_picking_view.xml',
        'views/transfer_status_routing_view.xml',
        'views/stock_picking_calender_view.xml',
        'views/account_move_view.xml',
        'views/stock_picking_type_view.xml',
        'views/transfer_shipping_requested.xml',
        'data/goflow_configuration_menu_items.xml',
        'data/cron.xml',
        'data/ir_sequence_data.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'bista_go_flow/static/src/js/sign_document.js',
            ],
    },

    'installable': True,
    'auto_install': False,
    'application': True,
}
