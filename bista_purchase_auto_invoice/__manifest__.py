# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Purchase Auto-Bill',
    'version': '16.0.0.1',
    'summary': 'Create Auto Vendor Bill From Incoming Shipment',
    'description': """
Purchase Order - Create Automatic Vendor Bill while validate Incoming Shipment
==============================================================================
This module allows you to create vendor bill automatically once incoming shipment
is processed.
    """,
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions',
    'depends': ['purchase_stock', 'account'],
    'category': 'Accounting',
    'data': [
            'views/res_config_settings_view.xml',
        ],
    'installable': True,
    'application':False,
}
