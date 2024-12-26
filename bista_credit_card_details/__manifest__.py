# -*- coding: utf-8 -*-
{
    'name': "Credit Card Details",
    'summary': """credit card details""",
    'license': 'LGPL-3',
    'category': 'contact',
    'author': '@ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['sale','web','base','authorize_net','payment'],
    'data': [
        'views/res_partner_view.xml',
        'data/email_template.xml',
    ],
    'installable': True,
    'application': True,
}
