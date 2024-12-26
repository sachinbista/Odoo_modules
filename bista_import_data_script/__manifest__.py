# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bista Import Data Script',
    'summary': 'Import Data Script',
    'description': """ Module to import product data.""",

    'version': '17.0.1.0.0',
    'category': 'Data',
    'author': 'Bista Solutions Pvt. Ltd.',

    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_product_data_view.xml',
    ],

    'installable': True,
    'license': 'LGPL-3',
}
