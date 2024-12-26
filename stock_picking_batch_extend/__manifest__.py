{
    "name": "Stock Picking Batch Extend",
    "version": "16.0.0.0.0",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": ['base','stock','stock_picking_batch','web'],
    "category": "Stock",
    "data": [
            'views/stock_picking_batch_view.xml',
            'views/stock_picking_view.xml',
            'views/stock_picking_type_view.xml'
             ],
    'assets': {
        'web.assets_backend': {
            'stock_picking_batch_extend/static/src/xml/batch_details_template.xml',
            'stock_picking_batch_extend/static/src/js/batch_details.js',
            'stock_picking_batch_extend/static/src/css/batch_popover_css.scss',
        }
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
