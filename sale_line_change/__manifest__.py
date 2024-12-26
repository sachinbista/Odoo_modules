{
    'name': 'Sale Line Change',
    'summary': 'Change Confirmed Sale Lines Routes or Warehouses.',
    'version': '17.0.1.0.0',
    'author': "Hibou Corp.",
    'category': 'Sale',
    'license': 'AGPL-3',
    'complexity': 'expert',
    'images': [],
    'website': "https://hibou.io",
    'description': """
""",
    'depends': [
        'sale_stock',
        'stock_dropshipping',
        'bista_shopify_connector',
    ],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_line_change_views.xml',
        'views/sale_views.xml',
    ],
    'auto_install': False,
    'installable': True,
}