# -*- coding: utf-8 -*-
{
    'name': "Bista : Partner Customization",
    'summary': """ """,
    'description': """ """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Partner',
    'images': ['static/description/icon.png'],
    'version': '17.0',
    'support': '',
    'depends': ['base','sale_management','contacts','base_vat','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/partner_view.xml',
        'views/invoice_payment_method.xml',
 
    ],
    'installable': True,
    'auto_install': False,
}
