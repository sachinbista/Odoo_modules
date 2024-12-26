{
    "name": "Purchase Order, Invoice and Delivery named like Sales Order",
    "summary": "Invoice and Deliveries created from Sales Order will receive names in line with Sales Order. Pricelist of Sales Order will also be added to Invoices.",
    "version": "16.0.0.0.0",
    "license": "AGPL-3",
    "category": "Uncategorized",
    "depends": ['account', 'sale', 'purchase', 'stock', 'bista_shopify_connector'],
    "application": True,
    "installable": True,
    'data': [
        'views/stock_picking_view.xml',
        'views/stock_route_view.xml'
    ],
}
