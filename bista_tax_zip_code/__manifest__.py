# -*- coding: utf-8 -*-

{
    "name": "Bista : Tax State ZIP Code.",
    "version": "17.0",
    "author": "Bista Solutions",
    "website": "https://www.bistasolutions.com",
    "category": "Productivity/Accouting",
    "license": "LGPL-3",
    "support": "  ",
    "summary": "Tax State ZIP Code",
    "description": """ Tax State ZIP Code """,
    "depends": [
        'sale',
        'account',
        'bista_shopify_connector',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/state_tax.xml',
        'views/res_partner.xml',
        'views/res_config_settings_views.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
