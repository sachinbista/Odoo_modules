# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################


{
    "name": "Bista Fedex Bill My Account",
    "summary": "Bill My Account functionality provide inside fedex shipping method.",
    'description': """
                Bill My Account functionality provide inside fedex when we select fedex shipping method
                inside partner and set account number then shipping charge pay from that account number. 
        """,
    "version": "16.0.1.0.1",
    "category": "Delivery",
    "website": 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt.Ltd',
    "license": "AGPL-3",
    "installable": True,
    "depends": ["delivery_fedex", 'bista_go_flow'],
    "icon": '/bista_fedex_my_account/static/description/icon.png',
    "data": [
        "views/delivery_carrier_view.xml",
        'wizard/choose_delivery_carrier_view.xml',
        "views/res_partner_view.xml",
        "views/sale_view.xml",
        "data/update_partner_phone.xml",
    ],
}
