# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Inventory Export",

    'summary': """Inventory/Product/ QTY On Hand Current Locations""",

    'description': """
        This report gives location wise current inventory of product
    """,

    'author': "Bista Solutions Pvt. Ltd.",
    'website': "http://www.bistasolutions.com",

    # Categories can be used to filter modules in modules listing
    'category': 'stock',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'account', 'purchase', 'product', 'point_of_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/inventory_data_cron.xml',
        'data/ir_sequence_data.xml',
        'views/stock_location.xml',
        'views/product_cost_log_view.xml',
        'views/product_product_view.xml',
        'views/product_template_view.xml',
        'views/bista_sftp_connection_views.xml',
        'views/product_alias_part_no_view.xml',
        'views/fabric_content_view.xml',
        'views/cleaning_code_view.xml',
        'views/color_name_view.xml',
        'views/pattern_view.xml',
        'views/collection_view.xml',
        'views/color_family_view.xml',
        'views/pattern_family_view.xml',
        'views/partner_product_relation_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}
