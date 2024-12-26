# -*- coding: utf-8 -*-
{
    'name': "Bista : Order Inactive Product",
    'summary': """ """,
    'description': """ """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Sale',
    'images': ['static/description/icon.png'],
    'version': '17.0',
    'support': '',
    'depends': ['sale','product_multi_company','bista_partner_customization'],
    'data': [
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'views/sale_order_view.xml',
        'views/product_allocation_view.xml',
        'wizard/order_review_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
