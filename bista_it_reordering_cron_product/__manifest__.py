##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Reordering_cron_track',
    'version': '1.0',
    'category': 'Sales',
    'depends': ['base', 'sale', 'stock'],
    'data': [
        'data/reordering_cron.xml',
        'view/stock_warehouse_orderpoint.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
