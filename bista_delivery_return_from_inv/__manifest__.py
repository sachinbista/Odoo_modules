# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "Delivery Return From Customer Invoice",
    "category": "Invoicing",
    "summary": "Delivery From Invoice",
    "description": """
        This module is used to return Delivery when we create credit note
    """,
    "version": "17.0.0.1",
    "author": "Bista Solutions",
    "website": "https://www.bistasolutions.com",
    "license": "AGPL-3",
    "depends": ["account","stock","bista_delivery_from_invoice","bista_customer_credit_limit"],
    "data": [
            'security/ir.model.access.csv',
            'wizard/insuffiecient_stock_wizard_views.xml',
    ],
    "auto_install": False,
    "installable": True,
}
