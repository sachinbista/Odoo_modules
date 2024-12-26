# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Product Markup/Margin',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'tools',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Product Markup/ Margin Calculation',
    'description': """
    Calculate Product Markup/Margin Based on sale and cost price
    """,
    'depends': [
        'sale', 'purchase', 'product'
    ],
    'data': [
        'views/product_template.xml',
        'views/product_varient_view.xml',
    ],

    'installable': True,
    'application': True,
}
