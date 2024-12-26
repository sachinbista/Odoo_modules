# -*- coding: utf-8 -*-
{
    'name': "Bista account Followup",
    'summary': """ customer followup report""",
    'description': """ customer followup report""",
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Account',
    'version': '17.0.1.0',
    'support': '',
    'depends': ['account_followup'],
    'data': [
        "security/ir.model.access.csv",
        'wizard/followup_wizard_view.xml',
        'views/followup_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
