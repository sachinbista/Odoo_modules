# -*- coding: utf-8 -*-

{
    'name': "Journal Restrictions",
    'summary': """Restrict users to certain journals""",
    'description': """Restrict users to certain journals.""",
    'author': "Bista",
    'website': "",
    'license': 'AGPL-3',
    'category': 'account',
    'version': '16.0.2.0',
    'depends': ['account'],
    'data': [
        'views/users.xml',
        'security/security.xml',
    ],
    "images": [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
