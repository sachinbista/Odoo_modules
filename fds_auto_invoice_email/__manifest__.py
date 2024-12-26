# -*- coding: utf-8 -*-
{
    'name': "FDS Auto Invoice Email",
    'summary': """FDS Auto Invoice Email""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': '@ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['account'],
    'data': [
        'data/mail_template_data.xml',
        'data/cron_data.xml',
        'views/account_move_view.xml',
    ],
    'assets': {
    },
    'installable': True,
    'application': True,
}
