# -*- coding: utf-8 -*-
{
    'name': "Bista Quality API",

    'summary': """APIs for quality management system.""",

    'description': """
        This module includes the following features:
            - API's for quality dashboard
            - API's for quality data
    """,

    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical',
    'version': '16.0.1.0.2',

    # any module necessary for this one to work correctly
    'depends': [
        'quality_control',
        'quality_control_picking_batch',
        'bista_wms_api',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
    ],
    # 'images': ['static/description/images/banner.gif'],
}
