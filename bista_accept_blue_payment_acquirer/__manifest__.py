
{
    "name": "Accept Blue Payment Acquirer",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["base",'account_payment','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/accept_blue_cofiguration.xml',
        'views/res_partner.xml',
        'views/customer_invoice.xml',
        'views/cron_accept_blue.xml',
        'views/account_payment_method_line.xml',
    ],
    "application": False,
    "installable": True,

}
