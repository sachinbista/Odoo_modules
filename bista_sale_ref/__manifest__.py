# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


{
    'name': 'Bista Sale Ref',
    'category': 'Sale order',
    'summary': 'Sale Ref',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ Sale Ref """,
    'depends': ['sale', 'base', 'account', 'bista_auto_invoice'],
    'data': [
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'views/account_move.xml',
        'reports/sale_report.xml',
        'reports/account_invoice_report.xml',

    ],
    'installable': True,
    'application': True,
}
