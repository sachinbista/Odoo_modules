# -*- coding: utf-8 -*-
{
    'name': "Bista : Inter Company Purchase Order",
    'summary': """ """,
    'description': """ """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Purchase Order',
    'images': ['static/description/icon.png'],
    'version': '17.0',
    'support': '',
    'depends': ['account','purchase','sale_purchase_inter_company_rules','stock_landed_costs'],
    'data': [
        'view/partner.xml',
        'view/company_view.xml',
        'view/account_journal_view.xml',
        'view/purchase_order.xml',
        'view/stock_picking.xml',
        'view/landed_cost_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
