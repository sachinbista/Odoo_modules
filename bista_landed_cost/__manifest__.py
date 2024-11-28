# -*- coding: utf-8 -*-
{
    'name': "Bista : Landed Cost",
    'summary': """ """,
    'description': """ """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Purchase Order',
    'images': ['static/description/icon.png'],
    'version': '17.0',
    'support': '',
    'depends': ['purchase','stock_landed_costs','bista_intercompany_po'],
    'data': [
        'security/ir.model.access.csv',
        'view/stock_lnded_cost_view.xml',
        'view/purchase_order.xml',
        'view/res_company_view.xml',
        'view/fiscal_position_view.xml',
        'wizard/transit_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
