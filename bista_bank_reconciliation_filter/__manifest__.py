# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bank Reconciliation Filter',
    "version": "16.0.0.1",
    'category': 'Account',
    'author': 'Bista Solutions Pvt. Ltd.',
    "website": "http://www.bistasolutions.com",
    'depends': ['account_accountant'],
    'description': """
    To add new filter and filter out the data based on the Allow Bank Recocnicliation given on the Chart Of Accounts. 

    """,
    'data': [
        'views/account_account_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
