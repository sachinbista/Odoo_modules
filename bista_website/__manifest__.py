{
    'name': "Bista Website",

    'summary': """
        this module is for pages and other design related to website design and content pages""",

    'description': """
        this module is for pages and other design related to website design and content pages
    """,

    'author': "Bistasolutions",
    'website': "https://www.bistasolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['website', 'website_sale', 'droggol_theme_common'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/about-us.xml',
        'views/best_seller.xml',
        'views/core-values.xml',
        'views/diamond_guarantee.xml',
        'views/faq.xml',
        'views/find_your_ring_size.xml',
        'views/our-founders.xml',
        'views/product_attribute_views.xml',
        'views/product_views.xml',
        'views/refer-friends.xml',
        'views/restoration.xml',
        'views/templates.xml',

        'templates/product_page.xml',
        'templates/appraisals.xml',
        'templates/jewelry_repair.xml',
        'templates/diamond_buy_back.xml',
        'templates/gift_cards.xml',
        'templates/sell_your_jewelry.xml',
        'templates/sale_return.xml',
        'templates/watches_services.xml',
        'templates/lifetime_warranty.xml',
        'templates/gift_card_message.xml',
        'templates/engraving.xml',
        'templates/free_resizing.xml',
        'templates/jewelry_insurance.xml',
        'templates/glossary.xml',
        'templates/learn_about.xml',
        'templates/diamond_services.xml',
        'data/data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bista_website/static/src/scss/style.scss',
            'bista_website/static/src/js/style.js',
            'bista_website/static/src/scss/style.scss',
        ],
    },
    'installable': True,
    'application': True,
}
# -*- coding: utf-8 -*-
