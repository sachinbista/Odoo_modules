# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Ship From Warehouse For Sale Order',
    'summary': '''
        Change warehouse for sale orders and regenerate the shipping for the selected warehouse.
    ''',
    'category': 'Sale',
    'version': '16.0',
    'license': 'AGPL-3',
    'author': 'Bista Solutions Pvt. Ltd.,',
    'maintainer': ['Bista Solutions Pvt. Ltd.', ],
    'website': 'www.bistasolutions.com',
    'depends': ['web', 'sale', 'stock', 'sale_stock','sale_line_report'],
    'data': [
        "security/ir.model.access.csv",
        'wizard/ship_from_warehouse_view.xml',
    ],
}
