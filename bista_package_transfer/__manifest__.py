##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': 'Bista Packages Transfer',
    'version': '14.0.1',
    'category': 'Inventory',
    'sequence': 1,
    'summary': """This module will help to transfer & merge the Packages.""",
    'description': "",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': 'http://www.bistasolutions.com',
    'depends': [
        'base',
        'stock',],
    'data': [
        'security/ir.model.access.csv',
        'wizard/package_transfer_wizard.xml',
        'views/stock_location_view.xml'
    ],
    'qweb': [
        "static/src/xml/base.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
