# -*- coding: utf-8 -*-
{
    'name': "bista_sale_split",

    'summary': """
        Split sale order module""",

    'description': """
        Split sale order module
    """,

    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',

    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['bista_go_flow'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
        'wizard/sale_split_wizard_view.xml',
    ],

}
