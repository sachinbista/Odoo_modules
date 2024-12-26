# -*- encoding: utf-8 -*-
{
    'name': "Bista Contacts",
    'summary': "This module helps to customize customer details",
    'description': """
This module helps to customize customer details.
""",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com/",
    'version': '16.0.1',
    'depends': [
        'base', 'contacts', 'account', 'purchase',
        'sale', 'crm', 'point_of_sale', 'website_partner',
        'purchase_stock', 'website_sale'
    ],
    'data': [
        'data/ir_config_data.xml',
        'security/ir.model.access.csv',
        'views/res_partner_event_view.xml',
        'views/res_partner_activity_history_view.xml',
        'views/res_company_view.xml',
        'views/partner_view.xml',
        ],
    'assets': {
        'web.assets_backend': [
            '/bista_contacts/static/src/xml/partner_chart.xml',
            '/bista_contacts/static/src/js/chart.js',
            '/bista_contacts/static/src/js/hooks.js',
            '/bista_contacts/static/src/js/button_box.js',
            '/bista_contacts/static/src/scss/variables.scss',
            '/bista_contacts/static/src/scss/org_chart.scss',
        ],
    },
    'license': 'AGPL-3',
}
