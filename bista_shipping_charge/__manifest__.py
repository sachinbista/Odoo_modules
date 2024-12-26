# -*- coding: utf-8 -*-
{
    'name': "Bista : Shipping Charge",
    'summary': """ Configure Shipping Charge for Customers""",
    'description': """ Activate and configure shipping charge customer wise. If shipping charge configured""",
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Sales',
    'images': ['static/description/icon.png'],
    'version': '17.0.1.0',
    'support': '',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/shipping_charge_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
