# -*- coding: utf-8 -*-
{
    'name': "Bista : Analytic Account Distribution",
    'summary': """ """,
    'description': """ """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Purchase Order',
    'version': '17.0',
    'support': '',
    'depends': ['sale','account','base','product_multi_company','account_reports'],
    'data': [
            'views/account_invoice_report_view.xml',
            'views/account_move_line_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
