# -*- coding: utf-8 -*-
{
    'name': "FDS Reports",
    'summary': """FDS Related Reports""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': 'Aemal Shirzai @ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['sale', 'purchase', 'stock', 'account', 'fds_stock'],
    'data': [
        'reports/external_layout.xml',
        'reports/sale_order.xml',
        'reports/purchase_order.xml',
        'reports/stock_picking.xml',
        'reports/invoice.xml',
        'reports/bill_of_landing.xml',
        'reports/commercial_invoice.xml',
        'views/paper_format.xml',
    ],
    'assets': {
         'web.report_assets_common': [
            'fds_reports/static/src/scss/style.scss',
        ],
    },
    'installable': True,
    'application': True,
}
