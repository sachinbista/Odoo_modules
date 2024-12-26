# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
{
    "name": "POS Signature",
    "summary": """The module allows you to save and display the Odoo POS user signature on receipt and on the order in the Odoo backend.""",
    "category": "Point of Sale",
    "version": "16.0.1.0.0",
    "sequence": 1,
    "author": "Webkul Software Pvt. Ltd.",
    "license": "Other proprietary",
    "website": "https://store.webkul.com/Odoo-POS-Signature.html",
    "description": """Odoo POS Signature
    Receipt signature
    POS user signature
    User sign on POS
    POS user signature on receipt
    Save user sign
    Save user signature
    POS Display user signature""",
    "live_test_url": "http://odoodemo.webkul.com/?module=pos_signature&custom_url=/pos/web/#action=pos.ui",
    "depends": ['point_of_sale'],
    "data": [
        'views/pos_customer_signature_view.xml',
    ],
    "images": ['static/description/Banner.png'],
    'assets': {
        'point_of_sale.assets': [
            'pos_signature/static/src/xml/pos_customer_signature.xml',
            'pos_signature/static/src/js/main.js',
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "price": 49,
    "currency": "USD",
    "pre_init_hook": "pre_init_check",
}
#################################################################################
