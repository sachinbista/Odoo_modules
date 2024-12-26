# -*- coding: utf-8 -*-
{
    'name': "Bista WMS Notification",

    'summary': """APIs for WMS mobile app notifications.""",

    'description': """
        This module includes the following features:
            - Handles notifications for various operations
    """,

    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical',
    'version': '16.0.1.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'bista_wms_api',
    ],

    # always loaded
    'data': [
        "views/res_users.xml",
        "views/res_config_settings_views.xml"
        # 'security/ir.model.access.csv',
    ],
    'images': ['static/description/images/banner.gif'],
}
