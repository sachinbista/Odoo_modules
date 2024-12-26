# -*- coding: utf-8 -*-
{
    'name': "purchase_order_receipt_expectation",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'stock', 'purchase_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/stock_picking_view.xml',
        'wizard/purchase_order_manual_receipt_view.xml',
    ],

    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
