# -*- encoding: utf-8 -*-
{
    'name': "Bista Consignment Report",
    'summary': "Consignment Report",
    'description': """
This module to Showing Consignment Report &
Based on configure Account set on Bill and Invoices.
""",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com/",
    'version': '16.0.1',
    'depends': ['base', 'sale_stock','purchase_stock', 'account'],
    'data': [
     'security/ir.model.access.csv',
     'reports/consignment_report_view.xml',
     'views/consignment_menu.xml',
     'views/res_company_views.xml',
     'views/stock_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
