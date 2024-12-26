# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Multiple Invoice Payment',
    'version': '15.0.0.1',
    'category': 'account',
    'sequence': 22,
    'author': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Odoo V 14.0 Pay multiple invoice using payment screen with any user defined amount',
    'description': """
       Odoo V 14.0 Pay multiple invoice using payment screen with any user defined amount'
               '1. User can able to allocate discount, sale tax and payment allocation'
               '2. Any outstanding payment or credit/refund can be utilized when processing payment'
               '3. Payment allocation feature can also be used once payment is posted.
     """,

    # any module necessary for this one to work correctly
    'depends': ['account', 'web', 'account_accountant', 'account_batch_payment'],

    # always loaded
    'data': ['views/account_payment_inehrit.xml',
             'views/res_config_settings_views.xml',
               'views/common_allocation_view.xml',
             'views/account_charges_type_view.xml',
             'security/ir.model.access.csv',
             'wizard/common_payment_process_wizard.xml',
             'wizard/import_invoice_credit_allocation.xml'
             # 'views/web_assets.xml',
             ],
    'assets': {
        'web.assets_backend': [
            # 'invoice_multi_payment/static/src/js/allocation_buttons.js',
            'invoice_multi_payment/static/src/js/new_allocation_button.js',
            'invoice_multi_payment/static/src/js/allocate_amount.js',
            'invoice_multi_payment/static/src/xml/**/*',
        ],
        'web.assets_qweb': [

        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
