##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Shopify Connector',
    'version': '17.0.1.0',
    'sequence': 1,
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
        'delivery',
        'sale',
        'stock',
        'stock_delivery',
        'account_accountant'
    ],
    'data': [
        'security/shopify_connector_security.xml',
        'security/ir.model.access.csv',
        'data/shopify_data.xml',
        'data/ir_sequence_data.xml',
        'data/shopify_import_export_cron.xml',
        'views/shopify_menuitems.xml',
        'wizard/import_export_operation_view.xml',
        'views/shopify_webhook_view.xml',
        'views/shopify_config_view.xml',
        'views/shopify_dashboard_view.xml',
        'views/shopify_error_log_view.xml',
        'views/shopify_queue_job_view.xml',
        'views/shopify_workflow_process_view.xml',
        'views/shopify_financial_workflow_view.xml',
        'views/shopify_payment_gateway_view.xml',
        'views/shopify_product_collection.xml',
        'views/shopify_product_tags_view.xml',
        'views/stock_warehouse_location_view.xml',
        'views/shopify_product_template_view.xml',
        'views/shopify_product_product_view.xml',
        'views/shopify_product_mapping_views.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/delivery_view.xml',
        'views/sale_order_view.xml',
        'wizard/product_export_ready_view.xml',
        'views/inventory_views.xml',
        'views/account_invoice.xml',
        'views/account_payment_view.xml',
        'views/shopify_payout_view.xml',
        'views/shopify_tags_view.xml',
        'views/stock_picking_view.xml',
        'wizard/export_shopify_product_template_view.xml',
        'wizard/export_shopify_product_variant_view.xml',
        'wizard/shopify_product_variant_sync_inventory_view.xml',
        'wizard/update_shopify_product_template.xml',
        'wizard/update_shopify_product_variant.xml',
        'wizard/shopify_export_refund_view.xml',
        'wizard/update_order_status_view.xml',
        'wizard/stock_return_picking_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/bista_shopify_connector/static/library/lightbox/css/lightbox.css',
            '/bista_shopify_connector/static/src/css/hoverbox.css',
            '/bista_shopify_connector/static/library/lightbox/js/jquery.lightbox.js',
            '/bista_shopify_connector/static/src/js/multi_image.js',
        ],
        'web.assets_qweb': [
            'bista_shopify_connector/static/src/xml/image_multi.xml',
        ],
        'web.assets_backend': [
            'bista_shopify_connector/static/src/components/tax_tools/custom_tax_tools_label.xml',
        ],
    },
    'qweb': ['static/src/xml/image_multi.xml'],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
    'price': 250,
    'currency': 'USD',
}
