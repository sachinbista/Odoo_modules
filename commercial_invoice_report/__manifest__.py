# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Commercial Invoice Report',
    'version': '15.0.0',
    'category': 'sale',
    'license': 'LGPL-3',
    'description': '''============================''',
    'author': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['base', 'stock', "web","product"],
    'data': [
        'report/template.xml',
        'report/commercial_invoice_report.xml',
        'views/product_product.xml',

    ],
    'installable': True,
    'auto_install': False,


}
