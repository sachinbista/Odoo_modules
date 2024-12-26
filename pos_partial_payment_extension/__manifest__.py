# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "POS Partial Payment Extension",
    "summary": """The module allows you to set remaining amount automatically in customer A/c.""",
    "category": "Point of Sale",
    "version": "16.0.1.0.0",
    "sequence": 1,
    "author": "Bista Solutions",
    "license": "Other proprietary",
    "website": "https://www.bistasolutions.com/",
    "description": """Odoo POS Partial Payment Extension""",
    "depends": ['pos_all_in_one','point_of_sale'],
    "data": [
            'views/pos_config_inherit.xml',
    ],
    "images": ['static/description/Banner.png'],
    'assets': {
        'point_of_sale.assets': [
            'pos_partial_payment_extension/static/src/js/PaymentScreen.js',
            'pos_partial_payment_extension/static/src/js/RegisterInvoicePaymentPopupWidget.js',
            'pos_partial_payment_extension/static/src/js/PosPayment.js',
            'pos_partial_payment_extension/static/src/xml/pos_payment.xml',
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
#################################################################################
