# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Website Image 360',
    'summary': 'This module helps to rotate the product image in 360 dimension view',
    'website': "https://www.bistasolutions.com/",
    'license': 'AGPL-3',
    'author': "Bista Solution Pvt. Ltd",
    'category': 'Website',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/website_image_360.xml',
        'views/template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bista_website_image_360/static/src/scss/style.scss',
            'bista_website_image_360/static/src/js/script.js',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
}
