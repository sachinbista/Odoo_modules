# -*- coding: utf-8 -*-

{
    'name': "Flybar Receivable Report",
    'category': 'Account',
    'summary': "Flybar Receivable Report",
    'description': """
Flybar Receivable Report,
===================================================================
    This module shows Aged Receivable report based on due date and invoice date with all details in list view.
    """,
    'version': '16.0',
    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',
    'depends': ['base', 'account', 'sale_management', 'account_reports', 'web'],
    'data': [
        'data/ir_cron.xml',
        'security/receivable_report_data_security.xml',
        'security/ir.model.access.csv',
        'views/account_receivable_view.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'flybar_receivable_report/static/src/js/receivable_report_list_renderer.js',
            'flybar_receivable_report/static/src/js/receivable_report_list_view.js',
            'flybar_receivable_report/static/src/js/receivalbe_report_list_controller.js',
            'flybar_receivable_report/static/src/xml/receivable_report_button.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
