{
    "name": "Bista Purchase Accounting Extension",
    "version": "16.0.0.0.0",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": ['base','purchase_order_receipt_expectation','account_accountant','account','bista_ship_allways', 'account_batch_payment','purchase_extension'],
    "category": "Stock",
    "data": [
            'data/templates.xml',
            'views/stock_picking_type_view.xml',
            'views/purchase_order_view.xml',
            'views/res_config_setting_view.xml',
            'views/account_move_view.xml',
            'views/stock_move_line_view.xml',
            'wizard/purchase_order_manual_receipt_view.xml',
             ],

    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
