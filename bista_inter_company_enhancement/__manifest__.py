# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    "name": "Bista Inter Company Enhancement",
    "summary": "Inter Company Enhancement",
    "version": "16.0.1.0.1",
    "category": "Accounting & Finance",
    'website': 'http://www.bistasolutions.com',
    'author': 'Bista Solutions',
    "license": "AGPL-3",
    'description': """ This module Offers PO/SO Synchronization, Invoice/Bill Synchronization,
                        Auto Validate Receipt and Auto Validate Bill""",
    "depends": ["sale", "account", "base_setup",
                "sale_purchase_inter_company_rules", "purchase",
                "purchase_stock", "sale_purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company.xml",
        "views/account_move_view.xml",
        "views/sale_view.xml",
        "views/purchase_view.xml",
        "views/stock_view.xml",
        "views/product_template_view.xml",
        "wizard/invoice_date_wizard_view.xml"
    ],

    "installable": True,
}
