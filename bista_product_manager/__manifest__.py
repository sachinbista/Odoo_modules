# -*- coding: utf-8 -*-
{
    'name': "Bista : Product Manager",
    'summary': """ Configure Product""",
    'description': """ Activate and configure to restrict the user to create or edit 
                       Product, Varient. """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Base',
    'images': ['static/description/icon.png'],
    'version': '17.0.1.0',
    'support': '',
    'depends': ['base','sale','product'],
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/product_new_menus.xml'
    ],
    'installable': True,
    'auto_install': False,
}
