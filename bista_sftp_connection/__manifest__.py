# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

{
    'name': "SFTP CONNECTION",

    'summary': """Sftp Connection""",

    'description': """
        Sftp Connection
    """,

    'author': "Bista Solutions Pvt. Ltd.",
    'website': "http://www.bistasolutions.com",

    # Categories can be used to filter modules in modules listing
    'category': 'stock',
    'version': "17.0",

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/bista_sftp_connection_views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [],
}
