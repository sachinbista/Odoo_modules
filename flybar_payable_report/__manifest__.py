# -*- coding: utf-8 -*-
{
    'name': "flybar_payable_report",
    'category': 'Account',
    'summary': "Flybar Payable Report",
    'description': """
Flybar Payable Report,
===================================================================
    This module shows Aged Payable report with all details in list view.
    """,
    'version': '16.0',
    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_reports'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/account_payable_view.xml',
    ],

    'assets': {
        'web.assets_backend': [

            'flybar_payable_report/static/src/js/payable_report_list_view.js',
            'flybar_payable_report/static/src/js/payable_report_list_controller.js',
            'flybar_payable_report/static/src/xml/payable_report_button.xml',

        ],
    },

    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
