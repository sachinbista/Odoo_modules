# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Website Configuration',
    "version": "16.0.0.0",
    'category': 'eCommerce',
    'author': 'Bista Solutions Pvt. Ltd.',
    "website": "https://www.bistasolutions.com",
    'depends': ['droggol_theme_common', 'appointment', 'website'],
    'description': """
        Website configuration demo Data
    """,
    'data': [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/mega_menu_v2.xml",
        "views/website_menu.xml",
        "templates/footers.xml",
        "templates/website_templates.xml",
        "templates/website_page.xml",

    ],
    'assets': {
        'web.assets_frontend': [
            'website_configuration/static/src/scss/darakjian_custom_mega_menu.scss',
            'website_configuration/static/src/scss/style.scss',
            'website_configuration/static/src/js/script.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}
