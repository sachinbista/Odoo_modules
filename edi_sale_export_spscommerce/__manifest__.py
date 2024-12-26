{
    'name': 'EDI Sale Export',
    'description': """
Allows Exporting EDI Purchase Order Acknowledgements to SPS Commerce
======================================================================
EDI Purchase Export (855)
An EDI 855 Purchase Order Acknowledgement is an EDI transaction set normally sent by a seller to a buyer in response to an EDI 850 Purchase Order. 
In addition to confirming the receipt of a new order, the document tells the buyer if the purchase order was accepted, required changes, or was rejected.
""",
    'category': 'Tools',
    'version': '2.0.0',
    'author': "Odoo PS",
    'website': "http://www.odoo.com",
    'license': 'OPL-1',
    'depends': ['edi_sale_spscommerce'],
    'data': [
        'data/edi_sale_data.xml',
        'data/edi_855.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
}
