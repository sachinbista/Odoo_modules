# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "Bista Freight Charges",
    "version": "16.0",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": ['base', 'sale', 'account', 'product'],
    "category": "account",
    "data": [
        'views/res_config_settings.xml',
        'views/account_move.xml',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": 'LGPL-3',
}
