# -*- coding: utf-8 -*-
{
    'name': 'Pos Customizations',
    'summary': """Customizations related to Pos""",
    'description': """Customizations related to PO""",
    'category': 'Stock',
    'version': '16.0',
    'depends': ['point_of_sale'],
    'data': [
        'views/report_sale_details.xml',
        'views/res_config_settings_view.xml',
        'data/report_notify_users.xml',
        'data/template_users_notify_mail.xml',
    ],
    'assets': {
            'point_of_sale.assets': [
                'pos_customization/static/src/xml/OrderReceipt_custom.xml',
            ]
        },

    'installable': True,
    'auto_install': False,
    'application': True,
}
