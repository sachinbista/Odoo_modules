# -*- coding: utf-8 -*-

{
    'name': "Flybar Account GroupBy Transaction",
    'category': 'Account',
    'summary': "Flybar Account GroupBy Transaction",
    'description': """
Flybar Account GroupBy Transaction,
===================================================================
    This module shows Account GroupBy Transaction report based on due date and invoice date with all details in list view.
    """,
    'version': '16.0',
    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',
    'depends': ['base', 'account', 'sale_management', 'account_reports', 'web'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_form_view.xml',
        'views/report_filter_view.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'flybar_account_groupby_transaction/static/src/js/account_report.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
