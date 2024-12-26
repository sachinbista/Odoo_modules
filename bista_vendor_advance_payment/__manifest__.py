# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': "Bista Vendor Advance Payment",
    'category': 'Purchase',
    'version': "16.0.0.0.1",
    'summary': """Customized Flow for Purchase Create Bills time asking Pre payment options.""",
    'description': """Customized Flow for Purchase Create Bills time asking Pre payment options.""",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    'depends': ['base', 'purchase', 'account'],
    'data': [
        # ============================================================
        # SECURITY
        # ============================================================
        'security/ir.model.access.csv',
        # ============================================================
        # VIEWS
        # ============================================================
        'wizard/purchase_make_invoice_advance_views.xml',
        'views/purchase_view.xml',
    ],
    'demo': [
    ],
    # Mark module as 'App'
    "application": True,
    "auto_install": False,
    "installable": True,
    "license": 'LGPL-3',
}



