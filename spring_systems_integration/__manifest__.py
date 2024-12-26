# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': "Spring Systems Integration",

    'summary': """Spring Systems Integration""",

    'description': """
        Spring Systems Integration
    """,

    'author': "Bista Solutions Pvt. Ltd",
    'website': "https://www.bistasolutions.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_stock', 'stock', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/spring_systems_configuration_views.xml',
        'views/spring_systems_sale_order_view.xml',
        'views/edi_855_view.xml',
        'views/edi_856_view.xml',
        'views/sale_order_view.xml',
        'views/res_partner_view.xml',
        'views/spring_systems_error_log.xml',
        'views/stock_picking_view.xml',
        'views/edi_810_view.xml',

        'data/spring_systems_cron.xml',
        'data/spring_systems_menuitems.xml',
    ],

    "application": True,
    "auto_install": False,
    "installable": True,
    "license": 'LGPL-3',
}
