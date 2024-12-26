{
    "name": "Sale Order Line & Purchase Order Lines View",
    "summary": "Display Sale Order Line & Purchase Order Lines Views with tree and pivot view",
    "version": "16.0.1.0.0",
    "category": "Sales",
    "description": "Display Sale Order Line & Purchase Order Lines Views with tree and pivot view",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",
    'company': 'Bista Solutions Pvt. Ltd.',
    'maintainer': 'Bista Solutions Pvt. Ltd',
    "depends": ['sale', 'purchase', 'spring_systems_integration','bista_go_flow_prodcut'],
    "data": [
        'security/ir.model.access.csv',
        'views/sale_order_line_view.xml',
        'views/purchase_order_line_view.xml',
        'wizards/purchase_exception_report.xml',
        'report/report.xml',
    ],

    'images': [],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}
