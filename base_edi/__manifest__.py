{
    'name': 'EDI Document Synchronization Base',
    'version': '2.0.0',
    'category': 'Tools',
    'description': """
Allows you to configure EDI document exchange configurations
==============================================================
You can perform your own EDI XML export and import via FTP.
""",
    'author': "Odoo PS",
    'website': "http://www.odoo.com",
    'license': 'OPL-1',
    'depends': ['mail'],
    'data': [
        #views
        'views/edi_config_view.xml',
        'views/res_partner_view.xml',
        #data
        'data/ir_cron_data.xml',
        'data/partner_address.xml',
        #security
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
