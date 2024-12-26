# -*- coding: utf-8 -*-
{
    'name': 'FDS: Stock',
    'summary': """Customizations related to Stock""",
    'description': """Customizations related to Stock""",
    'category': 'Stock',
    'version': '16.0',
    'depends': ['stock', 'stock_barcode', 'fds_sale'],
    'data': [
        'views/box_and_pallet.xml',
        # 'views/report_deliveryslip.xml',
        'reports/invoice.xml',
        'views/stock_picking_view.xml',
        'views/move_box_and_pallet_view.xml',
        'views/product_product_view.xml',
        'views/stock_quant_package_view.xml',
        'views/stock_package_type_view.xml',

        'wizards/set_package_value.xml',

        'security/ir.model.access.csv'
    ],
    'assets': {
        'web.assets_backend': [
            'fds_stock/static/src/**/*.js',
            'fds_stock/static/src/**/*.scss',
        ],
        'web.assets_qweb': [
            'fds_stock/static/src/**/*.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
