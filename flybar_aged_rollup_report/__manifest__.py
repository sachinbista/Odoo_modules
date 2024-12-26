# -*- coding: utf-8 -*-

{
    'name': "Flybar Aged Roll up  Report",
    'category': 'Account',
    'summary': "Flybar Aged Roll up Report",
    'description': """
Flybar Aged Roll up  Report,
===================================================================
    This module shows Aged report summary showing with starting and ending balance.
    """,
    'version': '16.0',
    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',
    'depends': ['base', 'flybar_general_ledger_report','flybar_receivable_report'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_receivable_view.xml',
        'views/aged_receivalbe_rollup_view.xml'

    ],
    'assets': {
        'web.assets_backend': [

        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
