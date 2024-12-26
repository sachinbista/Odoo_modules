# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista CRM',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'tools',
    'website': 'http://www.bistasolutions.com',
    'summary': 'CRM Enhancement',
    'description': """ This module allows to create Purchase Order from Opportunity.
   
    """,
    'depends': [
        'crm', 'purchase', 'stock','stock_account', 'product', 'sale', 'website_sale'
    ],
    'data': [
        'data/data.xml',
        'views/res_confing_settings_views.xml',
        'views/crm_lead_views.xml',
        'report/purchase_report_view.xml',
    ],
    'installable': True,
    'application': True,
}
