# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Split Lot",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "http://www.bistasolutions.com",
    'version': '16.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'product','mrp'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_view.xml',
        'views/mrp_production_view.xml',
        'wizard/split_lot_wizard_view.xml',
        'wizard/ask_scrap_wizard_view.xml',
        'wizard/scrap_lot_wizard_view.xml',
    ],
}
