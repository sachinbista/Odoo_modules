# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "Delivery From Customer Invoice",
    "category": "Invoicing",
    "summary": "Delivery From Invoice",
    "description": """
        This module is used to create Delivery from Customer Invoice
    """,
    "version": "17.0.0.1",
    "author": "Bista Solutions",
    "website": "https://www.bistasolutions.com",
    "license": "AGPL-3",
    "depends": ["account","stock"],
    "data": [
        "views/res_company_view.xml",
        "views/account_move_view.xml",
    ],
    "auto_install": False,
    "installable": True,
}
