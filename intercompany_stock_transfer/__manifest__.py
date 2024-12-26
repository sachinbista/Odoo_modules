# -*- coding: utf-8 -*-

{
    'name': 'Inter-Company Stock transfer',
    'version': '16.0.1.0.0',
    'category': 'Warehouse',
    'author': 'Bista Solutions Pvt. Ltd.',
    'website': 'https://www.bistasolutions.com/',
    'summary': """This module allows you to transfer stock between different
    companies.""",
    'description': """
Inter-Company Stock transfer
================================
Menu Path : Go to -> Inventory -> Operations -> Resupply Transfer\n
This module is able to transfer stock in 3-ways\n
1.Inter Warehouse Transfer
  with this type we are able to transfer stock between two warehouses
  with in the same company.which have the source location,source company
  destination location,destination company, lot-info and the quantity.
2.Inter Company  Transfer
  - with this type we are able to transfer stock between two companies,
  which
  have the source location,source company destination location,destination
  company, lot-info and the quantity.
  - inter company transfer also provides you alternative transfer location
  according to cross-doc configuration flow.
  - Inter company transfer functionality will create the payment for
  the stock transfers.

3.Inter Re-Supply Transfer
  with this type we are able to re-supply the stock between two
  locations in same company which have the source location,source company,
  destination location,destination company, lot-info and the quantity.

for transfer functionality we need to configure some parameters in
warehouse like, transit location,payment journal,account payable and
account receivable and etc,

=====================================================================
""",
    'depends': [
        'account',
        'stock_account',
        'quality',
        'sale',
        'bista_go_flow',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/res_company_view.xml',
        'views/inter_company_stock_transfer_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_warehouse_view.xml',
        'views/intra_inter_comp_action.xml',
        # 'views/stock_lot_view.xml',
        'views/stock_quant_view.xml',
        'views/account_move_view.xml',
        'views/resupply_add_multiple_product_view.xml',
        # 'report/report_stockpicking_transfer.xml',
    ],
    'license': 'AGPL-3',
}
