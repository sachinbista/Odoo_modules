# -*- coding: utf-8 -*-

{
    'name': "Flybar General Ledger Report",
    'category': 'Account',
    'summary': "Flybar General Ledger Report",
    'description': """
        Flybar General Ledger Report,
===================================================================
    This module shows General Ledger report.
    """,
    'version': '16.0',
    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',
    'depends': ['base', 'account', 'account_reports'],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/account_general_ledger_custom_view.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
