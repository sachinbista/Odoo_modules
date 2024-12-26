# -*- coding: utf-8 -*-

{
    'name': 'Part Replacement Report',
    'version': '16.0',
    'category': 'Part Replacement Report',
    'summary': 'Part Replacement Report',
    'description': """ """,
    'author': 'Bista Solutions Inc',
    'website': 'http://www.bistasolutions.com',
    'images': [],
    'depends': ['stock','sale', 'stock_inventory_valuation_report','stock_account'],
    'data': [
            # 'security/ir.model.access.csv',
            'views/part_replacement_views.xml',

        ],
    'demo': [],
    'test': [],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'AGPL-3',
}
