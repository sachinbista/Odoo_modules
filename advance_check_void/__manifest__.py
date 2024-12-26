# -*- coding: utf-8 -*-

{
    'name': 'Advance Check Void',
    'version': '1.5',
    'category': 'Accounting',
    'summary': 'Check History for Payments',
    'description': """
    This module use for vendor check payment management.
- Management Check history
- Check Void/Reversal Entry
- Partial Payment Void & Reverse
- Check Logs Management
""",
    'author': 'Bista Solutions Inc',
    'website': 'http://www.bistasolutions.com',
    'images': [],
    'depends': ['account', 'l10n_us_check_printing', ],
    'data': [
        'data/payment_methods_data.xml',
        'security/ir.model.access.csv',
        'wizard/account_move_reversal_view.xml',
        'views/account_payment_view.xml',
        'views/payment_check_history_view.xml'
        ],
    'demo': [],
    'test': [],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'AGPL-3',
}
