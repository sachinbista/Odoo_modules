# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    "name": "Bista Inventory Adjustment",
    "summary": "Bista Inventory Adjustment",
    "version": "16.0.1.0.1",
    "category": "",
    'website': 'http://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    "license": "AGPL-3",
    'description': """ Remove lot from non-tracking product""",
    "depends": ['stock', 'product'],
    "data": [
        'views/product_view.xml'
    ],
    "installable": True,
}
