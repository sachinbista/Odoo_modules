# -*- coding: utf-8 -*-
{
    'name': "Bista : Contact Product Manager",
    'summary': """ Configure Contact and Product""",
    'description': """ Activate and configure to restrict the user to create or edit 
                       Contact, Product, Varient,  and Product Category. """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Base',
    'images': ['static/description/icon.png'],
    'version': '17.0.1.0',
    'support': '',
    'depends': ['base','stock','base_setup','sale','product','stock_account','bista_product_manager'],
    'data': [

        'security/group.xml',
        'views/account_move_view.xml',
        'views/product_inherit_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
