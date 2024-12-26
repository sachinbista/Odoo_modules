# -*- coding: utf-8 -*-
{
    'name': "Bista : Customer Credit Limit",
    'summary': """ Configure Credit Limit for Customers""",
    'description': """ Activate and configure credit limit customer wise. If credit limit configured
    the system will warn or block the confirmation of a sales order if the existing due amount is greater
    than the configured warning or blocking credit limit. """,
    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",
    'license': 'AGPL-3',
    'category': 'Sales',
    'images': ['static/description/icon.png'],
    'version': '17.0.1.0',
    'support': '',
    'depends': ['account_accountant','base_setup'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/res_partner.xml',
        'views/account_move_view.xml',
        'wizard/credit_limit_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
