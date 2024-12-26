# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


{
    'name': 'Bista Purchase Add Lot',
    'category': 'Purchase',
    'summary': 'Adding new button',
    'version': '16.0.1.0.0',
    'author': 'Bista Solutions',
    'website': 'http://www.bistasolutions.com',
    'license': 'AGPL-3',
    'description': """ Adding new button""",
    'depends': ['stock', 'purchase', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'wizard/stock_picking_add_lot_wizard.xml'
    ],
    'installable': True,
    'application': True,
}
