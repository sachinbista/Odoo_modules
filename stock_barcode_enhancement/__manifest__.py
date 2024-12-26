{
    "name": "Customize Stock Barcode",
    "summary": "Customize Stock Barcode",
    "version": "16.0.1.0.0",
    "category": "Inventory",
    "description": "Customize Stock Barcode",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": [
        'stock_barcode',
    ],
    "data": [
        # 'security/ir.model.access.csv',
        # 'views/bol_report.xml',
    ],

    'assets': {
            'web.assets_backend': [
                'stock_barcode_enhancement/static/src/components/line.xml',
            ],
        },

    'images': [],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}