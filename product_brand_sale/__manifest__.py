# -*- coding: utf-8 -*
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Product Brand & Family',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': 'Product Brand & Family in Sale',
    'description': 'Product Brand & Family in Sales,brand,sale, odoo16',
    'author': 'Bistas solutions',
    'company': 'Bistas solutions',
    'maintainer': 'Bistas solutions',
    'images': ['static/description/banner.png'],
    'website': 'https://www.cybrosys.com',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/brand_views.xml',
        'views/sale_report_views.xml',
        'views/account_invoice_report.xml'
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,

}
