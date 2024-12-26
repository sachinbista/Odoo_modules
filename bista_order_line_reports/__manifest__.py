{
    "name": "Order Line Reports",
    "version": "16.0.1.0.7",
    "summary": "Order Line Reports",
    "author": "",
    "website": "",
    "category": "Order Line reports",
    "depends": ["sale","purchase","stock"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "wizards/sale_order_line_history.xml",
        "wizards/purchase_order_line_history.xml",
        'views/sale_order_line_report.xml',
        'views/purchase_order_line_report.xml',
    ],
    "installable": True,
    'application': True
}
