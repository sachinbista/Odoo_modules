##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Custom Quality Check Module',
    'version': '16.00',
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
    'depends': ['product',
                'sale_stock',
                'delivery',
                'quality_control',
               ],
    'data': ['security/ir.model.access.csv',
             "views/quality_check_views.xml",
             # "views/cargo_spectre_configuration.xml",
             # "wizard/cash_projection.xml",
            "wizard/quality_check_wizard_views.xml",
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
