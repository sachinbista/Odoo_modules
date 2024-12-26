# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Slip Invoice Report',
    'category': 'account',
    'summary': 'This module Offers Invoice customize report v17',
    'version': '17.0.1.0.1',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ This module Offers Invoice customize report v17
    """,
    'depends': ['account','base','web','stock','stock_delivery','bista_intercompany_po'],
    'data': [
        'report/new_invoice_report.xml',
        'report/report_invoice.xml',
        # 'report/ca_invoice_report.xml',
        'report/au_invoice_report.xml',
        # 'report/city_bank_30_days.xml',
        # 'report/usd_invoice_report.xml',
        'report/report_proforma_invoice.xml',
        # 'views/account_move_view.xml',
    ],
    'installable': True,
    'application': True,

}
