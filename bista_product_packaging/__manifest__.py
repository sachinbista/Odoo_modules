# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Product Packaging",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "http://www.bistasolutions.com",
    'version': '16.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'mrp', 'bista_stock_account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_product_view.xml',
        'views/stock_quant_package_view.xml',
        'views/mrp_production_view.xml',
    ],
}
