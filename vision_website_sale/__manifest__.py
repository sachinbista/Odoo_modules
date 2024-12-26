# -*- coding: utf-8 -*-
{
    'name': "vision_website_sale",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Bista Solutions",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Website',
    'version': '17.0.1.0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_sale', 'website_sale_stock', 'sale_management', 'delivery'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/product.xml',
        'views/partner.xml',
        'views/product_attribute.xml',
        'views/sale_order.xml',
        'views/templates.xml',
        'views/website_cart.xml',
        'data/product_publish.xml'

    ],
    'assets': {
        'web.assets_frontend': [
            'vision_website_sale/static/src/js/*.js',
            'vision_website_sale/static/src/scss/*.scss',
        ]
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
