# -*- coding: utf-8 -*-
{
    'name': "Bista Auto Invoice",
    'summary': """Auto Invoice sales order based on the payment terms""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': 'Omid Totakhel @ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['account', 'sale_stock', 'stock','sale','fds_auto_invoice_email'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_terms.xml',
        'views/stock_picking.xml',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': True,
}
