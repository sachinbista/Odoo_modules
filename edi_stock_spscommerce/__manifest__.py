{
    'name': 'EDI Stock',
    'description': """
Allows Exporting EDI Shipments to SPS Commerce
==============================================================
EDI Shipment Export (856)
The primary purpose of the EDI 856 advance ship notice (ASN) is to provide detailed information about a pending delivery of goods. 
The ASN describes the contents that have been shipped as well the carrier moving the order, the size of the shipment, ship date and in some cases estimated delivery date.
""",
    'category': 'Tools',
    'version': '2.0.0',
    'author': "Odoo PS",
    'website': "http://www.odoo.com",
    'license': 'OPL-1',
    'depends': ['delivery', 'edi_sale_spscommerce'],
    'data': [
        'data/edi_856.xml',
        'data/edi_stock_data.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
}
