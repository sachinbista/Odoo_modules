# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Add Reference of Journal Entries',
    "version": "16.0.0.1",
    'category': 'Repair',
    'author': 'Bista Solutions Pvt. Ltd.',
    "website": "http://www.bistasolutions.com",
    'depends': ['account_accountant'],
    'description': """
Idenitfy Purchase on Journal items(Stock related)
1. Identify journal item is linked to which purchase order(entries related to stock journal)
so Kavita can filter out those items and can perform further operations.

    """,
    'data': [
        'views/account_move_line.xml'
    ],
    'installable': True,
    'auto_install': False,
}
