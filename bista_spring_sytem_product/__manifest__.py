# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': "Spring Systems Product",

    'summary': """Spring Systems Integration""",

    'description': """
        Spring Systems Product Integration
    """,

    'author': "Bista Solutions Pvt. Ltd",
    'website': "https://www.bistasolutions.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'sale', 'spring_systems_integration'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/spring_system_product_view.xml',
        'views/spring_system_configuration_view.xml',
    ],

    "application": True,
    "auto_install": False,
    "installable": True,
    "license": 'LGPL-3',
}
