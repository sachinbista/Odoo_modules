# -*- coding: utf-8 -*-
{
    'name': 'eWAY Payment Acquirer',
    'version': '17.5',
    'category': 'Services',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'pragtech.co.in',
    'summary': 'Integrate eWAY payment gateway with Odoo for accepting payments from customers Odoo App payment acquirer eWAY payment acquirer eWAY payment gateway eWAY Payment Acquirer eWAY Acquirer eWAY payment getway',
    'description': """
        eWAY Payment Acquirer
        =====================
        Odoo Partners are imported and updated from and to Hubspot.
        Using Hubspot API data is synced.
        <keywords>
        Odoo Hubspot Integration App
        Braintree payment acquirer
        eWAY payment acquirer
        eWAY payment gateway
        eWAY Payment Acquirer
        eWAY Acquirer
        eWAY payment gateway
    """,

    'depends': ['payment'],
    'data': [
        'views/eway_payment_templates.xml',
        'views/eway_payment_provider_views.xml',
        'data/eway_payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'odoo_pragmatic_payment_eway/static/src/scss/payment_eway.scss',
            'odoo_pragmatic_payment_eway/static/src/js/eway_payment_form.js',
        ],
    },

    'images': ['static/description/Odoo-eWAY-Payment-Acquirer.jpg'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=310&name=eway-payment-acquirer',
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': '89',
    'installable': True,
    'application': True,
    'auto_install': False,
}
