# -*- coding: utf-8 -*-
{
    'name': "Bista Auto Invoice",
    'summary': """Auto Invoice sales order based on the payment terms""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': 'Omid Totakhel @ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['account', 'sale_stock', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_terms.xml',
        'views/stock_picking.xml',
        'views/res_config_settings_view.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': True,
}
