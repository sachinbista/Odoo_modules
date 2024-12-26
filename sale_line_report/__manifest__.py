{
    "name": "Sale Order Line Report",
    "summary": "Display On hand quantity and Backorder qty in sale order line report",
    "version": "16.0.1.0.0",
    "category": "Sales",
    "description": "Display On hand quantity and Backorder qty in sale order line report",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": [
        'sale_management',
        'stock',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/sale_line_report.xml',
        'views/truck_schedular.xml',
        'views/stock_route.xml',
        'views/stock_picking_view.xml'
    ],

    'images': [],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_init_hook': '_pre_init_sale_order_management',
}
