# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista SPS Connector',
    'category': 'Connector',
    'summary': 'This module Offers EDI Integration With SPS Commerce in v17',
    'version': '17.0.1.0.1',
    'author': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """The following document types are available:
    - 850 (Inbound Documents used to create SO in ODOO)
    - 856 (Delivery Transfer Validation Sent to SPS)
    - 810 (Invoice Sent to SPS)
    """,
    'depends': ['delivery', 'sale_stock'],
    'data': [
        'security/edi_res_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/data_queue_sequences.xml',
        'data/uom_code_data.xml',
        'views/edi_configuration_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'views/uom_uom_view.xml',
        'views/account_tax_views.xml',
        'views/account_invoice_view.xml',
        'views/stock_picking_view.xml',
        'views/data_queue_invoice_view.xml',
        # EDI 855
        'views/data_queue_order_ack_view.xml',
        'views/data_queue_order_view.xml',
        'views/data_queue_shipment_view.xml',
        'views/order_data_update_queue_view.xml',
        'views/master_data_view.xml',
        'views/sps_trading_partner_fields_view.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'application': True,
    'external_dependencies': {
        'python' : ['paramiko'],
    },
}
