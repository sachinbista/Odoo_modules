# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    "name": "Bista RapNet/Rapaport Integration",
    "version": "16.0",
    "author": "Bista Solutions",
    "website": "http://www.bistasolutions.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "product",
        "sale",
    ],
    "description": """
        The module used for getting diamond prices, inventory etc information from RapNet via Rapaport.
    """,
    "data": [
        "templates/instant_inventory_widget.xml",
        
        "data/rapaport.api.shape.csv",
        "data/rapaport.api.color.csv",
        "data/rapaport.api.clarity.csv",
        "data/page_data.xml",

        "security/ir.model.access.csv",

        "views/api_price_view.xml",
        "views/rapaport_api_data.xml",
        "views/rapaport_configuration.xml",
        "views/menus_view.xml",


    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}