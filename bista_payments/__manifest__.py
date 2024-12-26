# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "bista_payments",
    'summary': """Bista Payments""",
    'description': """Bista Payments""",
    'author': "Bista Solutions",
    'website': "http://www.bistasolutions.com",
    'category': 'Account Payment',
    'version': '16.0.0.1',

    'depends': ['base', 'account','bista_order_report'],

    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/cron_data.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings.xml',
        'wizard/account_payment_filter_wizard_view.xml',
    ],
}
