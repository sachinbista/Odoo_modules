{
    "name": "Shipping Manifest Batch",
    "summary": "Shipping Manifest Batch",
    "version": "16.0.1.0.0",
    "category": "Inventory",
    "description": "Display Shipping Manifest Batch",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": [
        'base','mail','stock','stock_picking_batch',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/shipping_manifest_batch_data.xml',
        'views/shipping_manifest_batch_view.xml',
    ],

    'images': [],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}