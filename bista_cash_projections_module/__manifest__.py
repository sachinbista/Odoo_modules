##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bista Cash Projections',
    'version': '15.0.0.1.6',
    'sequence': 7,
    'category': 'Odoo Connector',
    'summary': "This Module Allows you to connect Odoo with Shopify and sync "
               "data between Odoo and Shopify",
    'description': """
Publish your products on Shopify as well as create and process an orders in
 Odoo
=============================

The Shopify integrator gives you the opportunity to manage your Odoo's products
 on Shopify.

------------
* Publish products on Shopify
* Update inventory on Shopify
* Import of sales orders in Odoo and process invoices and delivery orders
    """,
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    'images': ['static/description/banner.png'],
    'depends': [
        'product',
        'sale_stock',
        'account',
        'delivery'],
    'data': ['security/ir.model.access.csv',
             "data/cash_projection_data_file.xml",
             "wizard/cash_projection_wizard_view.xml",
             # "wizard/cash_projection.xml",
             ],
    # 'external_dependencies': {
    #     'python': ['ShopifyAPI'],
    # },
    'assets': {
        'web.assets_backend': [

        ],
        'web.assets_qweb': [

        ],
    },
    'qweb': ['static/src/xml/image_multi.xml'],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
    'price': 250,
    'currency': 'USD',
}
