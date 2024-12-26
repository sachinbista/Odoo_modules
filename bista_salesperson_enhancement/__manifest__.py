# -*- encoding: utf-8 -*-
{
    'name': "Bista Salesperson Enhancement",
    'summary': "This module helps to add additional salesperson",
    'description': """
This module helps to to add additional salesperson.
""",
    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com/",
    'version': '16.0.1',
    'depends': ['base', 'sale','point_of_sale'],
    'data': [
            'views/sale_order_view.xml',
            'views/pos_order_view.xml',
        ],
    'assets': {
        'point_of_sale.assets': [
            'bista_salesperson_enhancement/static/src/js/**/*',
            'bista_salesperson_enhancement/static/src/xml/**/*',
            'bista_salesperson_enhancement/static/src/css/**/*',
        ],
    },
    'license': 'AGPL-3',
}
