# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Landed Costs On PO',
    'version': '1.0',
    'summary': 'Landed Costs on Purchase Order',
    'description': """
This module allows you to easily add extra costs on manufacturing order 
and decide the split of these costs among their stock moves in order to 
take them into account in your stock valuation.
    """,
    'depends': ['stock_landed_costs','bista_purchase_all_shipments'],
    'category': 'Purchase',
    'data': [
         'security/ir.model.access.csv',
        'views/stock_landed_cost_views.xml',
        'wizard/landedcost_warning_view.xml',
    ],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}
