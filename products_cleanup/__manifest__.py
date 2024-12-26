{
    'name': 'Products Cleanup',
    'version': '1.0',
    'category': 'product',
    'description': """  Module for Cleanup Odoo Products  """,
    'author': 'Ali Amer - Darakjian Jewelers',
    'depends': ['product','stock'],
    'data': ['security/ir.model.access.csv',
        'wizard/products_cleanup.xml',
    ],
    'installable': True,
    'application': False,
}