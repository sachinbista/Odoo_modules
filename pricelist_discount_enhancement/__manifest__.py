# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{

    # App information
    'name': 'Pricelist Enhancement in Invoice',
    'version': '17.0.1.0',
    'category': 'Sales',
    'license': 'OPL-1',
    'summary': "Manage pricelist and discount in Odoo.",

    # Author
    'author': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': "https://www.bistasolutions.com/",
    # Dependencies
    'depends': ['sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/product_pricelist_view.xml',
        'views/country_tax_view.xml',

    ],

    'installable': True,
    'auto_install': False,
    'application': True,
    'active': False,
}
