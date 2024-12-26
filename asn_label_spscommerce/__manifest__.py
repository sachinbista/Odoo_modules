{
    'name': 'EDI ASN Label',
    'description': """
Generates ASN Labels for Shipments
==============================================================
Uses the SPS Commerce API to generate an ASN Label for delivery orders.
It produces a file in PDF and ZPL formats when the PACK stage is confirmed.
""",
    'version': '2.0.0',
    'category': 'Tools',
    'author': "Odoo Inc",
    'website': "http://www.odoo.com",
    'license': 'OEEL-1',
    'depends': ['edi_stock_spscommerce'],
    'data': [
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'data/print_asn.xml',
        'views/asn_label_report.xml',
        'views/edi_config_view.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
}
