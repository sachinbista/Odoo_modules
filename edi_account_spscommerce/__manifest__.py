{
    'name': 'EDI Invoicing',
    'description': """
Allows Exporting EDI Invoices to True Commerce
==============================================================
EDI Invoice Export (810)
The 810 Invoice document is typically sent in response to an EDI 850 Purchase Order as a request for payment once the goods have shipped or services are provided.
""",
    'category': 'Tools',
    'version': '2.0.0',
    'author': "Odoo PS",
    'website': "http://www.odoo.com",
    'license': 'OPL-1',
    'depends': ['account', 'edi_sale_spscommerce'],
    'data': [
        'data/edi_invoice_data.xml',
        'data/edi_810.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
}
