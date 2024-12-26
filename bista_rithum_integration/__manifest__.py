# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Rithum Integration",
    'category': 'Sale',
    'summary': "Sale customization",
    'description': """
        Bista Rithum Integration
    """,
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    'depends': ['base', 'sale', 'account', 'delivery', 'bista_reports', 'bista_sale_order_pivot', 'bista_auto_invoice',
                'bista_shipstation', 'bista_remove_merge_move'],
    'data': [
        'security/ir.model.access.csv',
        'security/rithum_security.xml',
        'data/rithum_import_order_cron.xml',
        'data/rithum_update_product_qty_cron.xml',
        'views/rithum_config_view.xml',
        'wizards/rithum_order_sync_wizard.xml',
        'wizards/import_single_order_wizard.xml',
        'views/product_product_view.xml',
        'views/sale_order_view.xml',
        'views/rithum_product_product_view.xml',
        'views/rithum_error_order_log.xml',
        'views/rithum_error_invoice_log.xml',
        'views/rithum_error_inventory_log.xml',
        'views/import_order_server_action.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
