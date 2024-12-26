{
    "name": "Stock Picking Extend",
    "version": "16.0.0.0.0",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": ['base','stock','bista_go_flow','stock_picking_batch','stock_landed_costs','intercompany_stock_transfer','sync_inventory_adjustment'],
    "category": "Stock",
    "data": [
            'security/ir.model.access.csv',
            'views/stock_picking_view.xml',
            'views/stock_picking_type_view.xml',
            'views/stock_move_view.xml',
            'views/container_view.xml',
            'views/product_view.xml',
            'views/stock_quant_view.xml',
            'wizard/package_split_wizard_view.xml',
            'wizard/pin_message_wizard_view.xml',
            'wizard/stock_inventory_adjustment_name.xml',
             ],
    'assets': {
            'web.assets_backend': [
                'stock_picking_extend/static/src/scss/button_class.css',

            ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
