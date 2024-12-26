{
    'name': 'EDI Stock Import',
    'description': """
Allows Importing EDI Shipments to SPS Commerce
==============================================================
EDI Shipment Import (945)
The EDI 945 transaction set, referred to as Warehouse Shipping Advice transaction, provides confirmation of a shipment. 
This transaction is used by a warehouse to notify a trading partner that a shipment was made.
""",
    'category': 'Tools',
    'version': '2.0.0',
    'author': "Odoo Inc",
    'website': "http://www.odoo.com",
    'license': 'OPL-1',
    'depends': ['edi_stock_spscommerce'],
    'data': [
        'data/actions.xml',
        'data/edi_stock_data.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
}
