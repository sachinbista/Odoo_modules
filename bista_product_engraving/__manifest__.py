{
    'name': 'Bista Product Engraving',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Bista Product Engraving',
    'description': """
    Bista Product Engraving
    =======================
    """,
    'author': 'Bista Solutions Pvt. Ltd.',
    'website': 'http://www.bistasolutions.com',
    'depends': ['base', 'sale', 'web', 'website', 'website_sale', 'droggol_theme_common','product'],
    'data': [
        'security/ir.model.access.csv',

        'data/engrave_data.xml',
        'data/engrave_font_data.xml',
        
        # 'views/product_attribute.xml',
        'views/product_template.xml',
        'views/engrave_font_view.xml',

        'templates/engraving_template.xml',
        'templates/website_sale.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bista_product_engraving/static/src/js/engraving.js',
            'bista_product_engraving/static/src/scss/engraving.scss',

            'bista_product_engraving/static/src/js/website_sale.js',
        ],
        'web._assets_primary_variables': [
            # ("prepend", "bista_product_engraving/static/src/scss/engraving_fonts.scss"),
            ("prepend", "bista_product_engraving/static/src/scss/engrave_font_template.scss"),
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}