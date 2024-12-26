# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2012 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Data Import',
    'version': '1.1',
    'category': 'Product',
    'summary': 'Data Import',
    'description': """

    """,
    'author': "Bista Solutions",
    'website': 'http://www.bistasolutions.com',
    'depends': ['base'],
    'data': ['security/ir.model.access.csv',
        'wizard/import_data.xml',

    ],
    'installable': True,
}
