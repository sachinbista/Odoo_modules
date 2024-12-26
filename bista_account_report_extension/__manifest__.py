# -*- coding: utf-8 -*-

{
    "name" : "Financial Report Extension",
    "version" : "16.0.0.3",
    "category" : "Accounting",
    'summary': 'Enhancement Aged Receivable Reports',
    "description": """
      Enhancement Aged Receivable Reports to exclude Services
    """,
    "author": "BistaSolutions",
    "website" : "https://www.bistasolutions.com",
    "depends" : ['account', 'account_accountant', 'account_reports'],
    "data": [
        'views/account_report_view.xml'
    ],
    "auto_install": False,
    "installable": True,
}
