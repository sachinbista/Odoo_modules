# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Email validation',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'tools',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Work Email validation',
    'description': """
    Check if Email is valid and make it Small-letters
    """,
    'depends': [
    'base', 'mail', 'mass_mailing', 'base_setup', 'contacts'
    ],
    'data': [
    'views/res_config_settings.xml',
    'views/res_partner.xml',
    ],
    'installable': True,
    'application': True,
}
