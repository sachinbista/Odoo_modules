# -*- coding: utf-8 -*-
{
    "name": "Sale Order To Purchase Order",
    "author": "Bista Solutions",
    "category": "Purchases",
    "license": 'LGPL-3',
    "summary": """Quick Sale Order To Purchase Order module, So to PO, Quotation to Request for quotation app, Sales to purchase, sales order to purchase order, quotation to rfq odoo""",
    "description": """This module is useful to create quickly purchase orders from the sale order.""",
    "version": "16.0.2",
    "depends": [
        "sale_management",
        "purchase_order_receipt_expectation",
    ],
    "application": True,
    "data": [
        "security/ir.model.access.csv",
        "security/dropship_security.xml",
        "views/sale_view.xml",
        "views/purchase_views.xml",
        "wizard/purchase_order_wizard.xml",
        "views/res_company_view.xml",
    ],
    "images": ["static/description/background.jpg", ],
    "auto_install": False,
    "installable": True
}
