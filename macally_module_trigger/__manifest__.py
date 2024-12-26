# -*- coding: utf-8 -*-
{
    'name': 'Macally Module Trigger',
    'version': '1.0',
    'summary': 'Macally Module Trigger',
    'sequence': 10,
    'description': """Macally Module Trigger """,
    'category': '',
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    'images': [],
    'depends': ['base', 'bista_shopify_connector', 'queue_job',
                'macally_reports_extension', 'shopify_queue_job_extend',
                'bista_vendor_advance_payment', 'bista_purchase_auto_invoice',
                'product_logistics_uom', 'product_packaging_dimension',
                'sale_order_extensions', 'payment_term_delivery_exception',
                'inventory_extension', 'sale_line_change',
                'stock_split_picking', 'bista_sps_connector'],
    'data': [
    ],
    'demo': [

    ],
    'qweb': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook_config',
}
