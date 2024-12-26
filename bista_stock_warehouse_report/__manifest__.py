# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "Bista Stock Warehouse Report",
    "version": "16.0.0.0.1",
    "category": "Stock Warehouse Report",
    "license": "LGPL-3",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "summary": "Stock Warehouse Report",
    "depends": ["product", "stock",],
    "data": [
        "security/ir.model.access.csv",
        "views/product_warehouse_qty_view.xml"
    ],
    "application": True,
    "auto_install": False,
    "installable": True,
}
