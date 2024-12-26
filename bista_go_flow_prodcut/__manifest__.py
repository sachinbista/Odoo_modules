# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Go Flow Product",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Bista Solutions",
    'website': "https://www.bistasolutions.com",

    'category': 'API Integeration',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'bista_go_flow','delivery'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/goflow_product_data.xml',
        'views/goflow_product_map_line_views.xml',
        'views/goflow_product_views.xml',
        'views/goflow_configuration_views.xml',
        'views/product_brand_view.xml',
        'views/product_manufacturer_view.xml',
        'views/product_view.xml',
        'data/cron.xml',
        'data/goflow_menuitems.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
