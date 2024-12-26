# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Custom Fields Mapping',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'general',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Custom fields mapping',
    'description': """
    Custom fields mapping
    """,
    'depends': ['base', 'sale_management', 'hr', 'sale_stock', 'purchase', 'product_margin', 'stock', 'product_brand_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/aged_inventory_report.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml'

    ],
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}
