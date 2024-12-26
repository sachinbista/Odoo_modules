{
    "name": "Bista Order Report",
    "summary": "Bista Order Report",
    "version": "16.0.0.0.0",
    "license": "AGPL-3",
    "category": "Uncategorized",
    "depends": ['base', 'sale', 'stock', 'sale_stock'],
    "application": True,
    "installable": True,
    'data': [
        'views/sale_order_line_view.xml',
        'views/stock_move_view.xml',
        'views/account_move_view.xml'
    ],
}