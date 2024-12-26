# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': "Bista Import Payment",
    'category': 'Account',
    'version': "16.0.0.0.1",
    'summary': """Import payment from csv file.""",
    'description': """Import payment from csv file.""",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    'depends': ['base', 'account', 'account_batch_payment', 'invoice_multi_payment'],
    'data': [
        # ============================================================
        # SECURITY
        # ============================================================
        'security/ir.model.access.csv',
        # ============================================================
        # VIEWS
        # ============================================================
        'views/res_config_settings_view.xml',
        'views/inherit_payment_report.xml',
        'wizard/import_payment.xml',
        'wizard/account_payment_register_views.xml',
        'wizard/import_invoice_credit_note.xml'
    ],
    'demo': [
    ],
    # Mark module as 'App'
    "application": True,
    "auto_install": False,
    "installable": True,
    "license": 'LGPL-3',
}



