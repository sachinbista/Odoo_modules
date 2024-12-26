# -*- coding: utf-8 -*-

{
    'name': 'Bista List One2many',
    'summary': '''
    ''',
    'category': 'Tools',
    'version': '16.0.0.1.0',
    'license': 'AGPL-3',
    'author': 'Bista Solutions Pvt. Ltd.,',
    'maintainer': ['Bista Solutions Pvt. Ltd.',],
    'website': 'www.bistasolutions.com',
    'images': ['static/description/icon.png'],
    'depends': ['web', 'sale', 'sale_stock', 'sale_line_report'],
	'data': [
        # "views/sale_order_views.xml",
        "views/sale_line_report_tree_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            # Fields
            'bista_list_one2many/static/src/js/fields/**/*.js',
            'bista_list_one2many/static/src/js/fields/**/*.xml',

            # Views
            'bista_list_one2many/static/src/js/views/**/*.js',
            'bista_list_one2many/static/src/js/views/**/*.xml',

            #  #scss
            'bista_list_one2many/static/src/js/views/**/*.scss',
            'bista_list_one2many/static/src/widgets/bista_qty_at_date_widget.js',
            'bista_list_one2many/static/src/widgets/qty_at_date_widget.js',
            'bista_list_one2many/static/src/xml/bista_branch_qty_at_date.xml',
        ],
    },
}
