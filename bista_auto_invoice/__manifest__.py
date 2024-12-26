# -*- coding: utf-8 -*-
{
    'name': "Auto Invoice",
    'summary': """Auto Invoice Feature""",
    'license': 'LGPL-3',
    'category': 'account',
    'author': 'Aemal Shirzai @ Bista Solutions',
    'website': 'https://www.bistasolutions.com',
    'depends': ['account', 'sale', 'stock', 'bista_inter_company_enhancement'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_terms.xml',
        'views/res_config_settings.xml',
        'views/stock_picking.xml',
        'wizards/transfer_validate_confirm.xml'
    ],
    'installable': True,
    'application': True,
}
