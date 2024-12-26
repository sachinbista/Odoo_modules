{
    "name": "Custom Bista GoFlow Import",
    "summary": "Custom Custom Bista GoFlow Import",
    "version": "16.0.1.0.0",
    "category": "Inventory",
    "description": "Display Custom Bista GoFlow Import",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": [
        'base',
        'bista_go_flow',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/go_flow_import_view.xml',
        'views/go_flow_invoice_import_viiew.xml',
    ],

    'images': [],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}