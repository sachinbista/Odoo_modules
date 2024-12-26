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
    'version': '16.0',
    'support': '',
    'depends': ['base','sale_management','stock','sale_stock','account','sale','bista_order_report'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'wizard/sale_order_wizard_view.xml',
        'wizard/warning_wizard.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/ir_cron.xml',
        'views/res_config_settings.xml',
        'views/res_partner_blocking_thr_view.xml',
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
