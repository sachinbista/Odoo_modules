# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Partner Credit Limit',
    'version': '16.0.1.0.0',
    'category': 'Partner',
    "summary": "PP modifications for customer credit limit",
    "description": """PP modifications for customer credit limit""",
    "version": "16.0.0.0.1",
    "author": 'Bista Solutions Pvt. Ltd.',
    "website": 'https://www.bistasolutions.com',
    "company": 'Bista Solutions Pvt. Ltd.',
    "maintainer": 'Bista Solutions Pvt. Ltd',
    'depends': [
        'sale_management', 'account_followup'
    ],
    'data': [
            'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
