# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

{
    'name': "Bista Ship Allways",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Srinivas Chandi",
    'website': "https://www.bistasolutions.com",

    'category': 'API Integeration',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'stock', 'stock_picking_batch_extend', 'spring_systems_integration','printnode_base'],

    # always loaded
    'data': ['views/shipalways_configuration.xml',
             'views/stock_picking_batch_view.xml',
             'views/schedular.xml',
             ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
