# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Reports',
    'category': 'Sale order',
    'summary': 'Qweb pdf report',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ PDF Report """,
    'depends': ['sale', 'base', 'stock', 'web', 'sale_stock', 'account', 'sale_order_line_sequence','account_followup','bista_auto_invoice','mail'],
    'data': [
        'security/inventory_group.xml',
        'data/mail_template_data.xml',
        'data/cron_data.xml',
	    'data/sale_email_template_data.xml',
	    'data/stock_picking_email_template_data.xml',
	    'data/purchase_order_email_template_data.xml',
	    'data/account_email_template_data.xml',
	    'data/res_users_email_template_data.xml',
        'data/mail_template_migrate_way.xml',
        'views/stock_picking_view.xml',
        'views/res_partner_view.xml',
        'views/account_payment_register_view.xml',
        'views/account_payment_view.xml',
        'views/account_move_view.xml',
        'views/res_company_view.xml',
        'report/report_paper_format.xml',
        'report/report_action.xml',
        'report/report_payment_receipt.xml',
        'report/account_invoice_report.xml',
        'report/picking_operation_report_action.xml',
        'report/picking_operation_report.xml',
        'report/dropship_operation_report.xml',
        'report/intercompany_operation_report.xml'
    ],
    'installable': True,
    'application': True,
}
