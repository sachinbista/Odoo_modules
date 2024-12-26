# -*- coding: utf-8 -*-
{
    'name': "purchase_extension",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': 'Bista solutions Pvt Ltd',
    'website': 'https://www.bistasolutions.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'purchase_stock','bista_sale_dropship'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/po_report_override.xml',
        'report/purchase_paperformate_file.xml',
        # 'report/purchase_quotation_template.xml',
        'views/purchase_order_view.xml',
        'views/add_dynamic_note_view.xml',
        'wizard/cancel_reason_wizard_view.xml',
        'wizard/add_dynamic_note_wiz_view.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    "application": True,
    "auto_install": False,
    "installable": True,
    "license": 'LGPL-3',
}
