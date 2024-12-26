# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Product Ref on Mrp Calendar',
    'version': '1.0',
    'category': 'CRM',
    'license': 'LGPL-3',
    'description': '''
        This module address product internal reference to the mrp calendar view
    ''',
    'author': 'Omid Totakhel @ Bista Solutions',
    'maintainer': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['base', 'mrp', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': ['bista_product_ref_mrp_calendar/static/src/js/*.js']
    },
    'installable': True,
    'auto_install': False,
}
