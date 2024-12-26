# -*- coding: utf-8 -*-
{
    'name': 'FDS: Sale',
    'summary': """Customizations related to Sale""",
    'description': """Customizations related to Sale""",
    'category': 'Sale',
    'version': '16.0',
    'depends': [
        'sale',
        'account',
        'mrp',
        'sale_management',
        'sale_stock',
        'sale_product_configurator',
        'purchase_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        # datas
        'datas/fds_sale_data.xml',
        'datas/stock_picking_type_data.xml',

        # views
        'views/sale_order_view.xml',
        'views/res_partner_view.xml',
        'views/stock_orderpoint_view.xml',
        'views/stock_warehouse_view.xml',
        'views/product_product_view.xml',
        'views/mrp_bom_line_view.xml',

        # templates'
        'views/sale_portal_templates.xml',
        'views/sale_portal_quote_edit_template.xml',
        'views/product_price_entry_template.xml',

        # wizards
        'wizards/sale_product_price_entry_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fds_sale/static/src/js/product_price_entry.js',
            'fds_sale/static/src/js/sale_product_field.js',
        ],
        'web.assets_frontend': [
            'fds_sale/static/src/js/edit_sale_order.js',
            'fds_sale/static/src/js/sale_portal.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
