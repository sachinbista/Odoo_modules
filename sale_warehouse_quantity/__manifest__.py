{
    "name": "Sale Warehouse Quantity",
    "summary": "Show available quantity of all warehouse on sale order line",
    "version": "16.0.1.0.0",
    "category": "website",
    "website": "http://codegiday.com",
    "author": "Vo Minh Bao Hieu",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "sale_stock",
    ],
    "data": [
        # Views
        "views/sale_order.xml",
    ],
}
