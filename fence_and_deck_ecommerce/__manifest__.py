{
    'name': 'Fence and Deck Supply eCommerce Payment Acquirers',
    'summary': '''Fence and Deck Supply : Restrict online payment options for different contacts''',
    'description': '''
        Fence and Deck Supply:
            If boolean TERMS field in res.user is set to TRUE, any payment acquirer set and configured in Odoo should not appear as a payment option for the portal user when paying online any quote or invoice.

            If boolean TERMS field in res.user is set to FALSE, all payment options should appear to the portal user. 

        Developer: ELCE
        Ticket ID: 2950788
    ''',
    'author': 'Odoo',
    'website': 'https://www.odoo.com',
    'category': 'Custom Development',
    'version': '1.1.0',
    'depends': ['website_sale'],
    'data': [
        'views/res_partner.xml',
        'views/payment_provider.xml',
    ],
    'license': 'OPL-1',
}
