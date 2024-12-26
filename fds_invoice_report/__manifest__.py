# -*- coding: utf-8 -*-
{
    'name': 'FDS: Invoice Report',
    'summary': """Customizations related to invoice report""",
    'description': """Customizations related to invoice report""",
    'category': 'Stock',
    'version': '16.0',
    'depends': ['base','account','bista_fds_crm','web'],
    'data': [
        'reports/invoice.xml',
    ],
    'installable': True,    'auto_install': False,
    'application': True,
}
