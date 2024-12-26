{
    "name": "Stock Inventory Valuation Report",
    "version": "16.0.1.0.0",
    "summary": "Inventory Valuation Report",
    "author": "",
    "website": "",
    "category": "Warehouse Management",
    "depends": ["stock_account", 'stock_landed_costs'],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "security/access_total_value_unit_cost.xml",
        "data/product_type_data.xml",
        "wizards/stock_valuation_history.xml",
        'views/stock_landed_cost_view.xml',
        "views/stock_valuation_report.xml",
        'views/stock_valuation_layer_view.xml',
        'views/product_template_views.xml',
    ],
    "installable": True,
    'application': True
}
