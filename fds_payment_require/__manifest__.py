# -*- coding: utf-8 -*-
{
    'name': "Payment Require",
    'summary': """FDS Payment Require""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': 'Aemal Shirzai @ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['sale', 'base','account', 'web', 'portal','website_sale'],
    'data': [
        'views/sale_order_view.xml',
        'views/payment_term_view.xml',
        'views/res_partner_view.xml',
        'views/portal_template.xml',
        'views/sale_portal_template.xml',
    ],
    'assets': {
            'web.assets_frontend': [
            'fds_payment_require/static/src/xml/name_and_signature.xml',
            'fds_payment_require/static/src/xml/name_and_signature.js',
            'fds_payment_require/static/src/xml/portal_signature.js',
        ],
    },
    'installable': True,
    'application': True,
}
