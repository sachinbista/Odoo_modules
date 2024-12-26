# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Remove Merge Move",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "http://www.bistasolutions.com",
    'version': '16.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'sale', 'sale_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/stock_quant_package_view.xml',
        'views/stock_picking_type_view.xml',
        'views/stock_picking_view.xml',
        'wizard/package_wizard_view.xml',
    ],

}
