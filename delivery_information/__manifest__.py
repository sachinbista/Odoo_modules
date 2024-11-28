# -*- coding: utf-8 -*-
{
    "name": "Delivary Tracking - Enhancement",
    "version": "17.0",
    "author": "Bista Solutions",
    "website": "https://www.bistasolutions.com",
    "category": "Inventory",
    "license": "LGPL-3",
    "support": "  ",
    "summary": "Delivary Information Enhancement",
    "description": """ Delivary Information Enhancement """,
    "depends": [
        'stock',
        'delivery_fedex',
        'sale_stock',
    ],
    "data": [
        'wizard/wizard_view.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/carrier_view.xml',
        'views/picking.xml',
        'views/ups_picking.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
