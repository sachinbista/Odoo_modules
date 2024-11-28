# -*- coding: utf-8 -*-
{
    'name': "Bista batch payment report",
    'summary': """ batch payment excel report""",
    'description': """ batch payment excel report""",
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Account',
    'images': ['static/description/icon.png'],
    'version': '17.0.1.0',
    'support': '',
    'depends': ['account_batch_payment','account'],
    'data': [
        'data/accounting_email_template.xml',
        'views/batch_payment_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
