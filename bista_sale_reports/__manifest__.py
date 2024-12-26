# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
{
    'name': 'Bista Sale Reports',
    'version': '16.0',
    'author': 'Bista Solutions Pvt. Ltd.',
    'sequence': 1,
    'category': 'Sale Reports',
    'website': 'http://www.bistasolutions.com',
    'summary': 'Sale Reports',
    'description': """ 
        This module is used to generate sale reports. 
    """,
    'depends': [
        'base', 'sale', 'product', 'sales_team', 'account_reports', 'bista_product_markup_margin',
        'account', 'account_accountant', 'gamification', 'voip',
    ],
    'data': [
        'data/sales_performance_report.xml',
        'data/client_ranking.xml',
        'data/client_history.xml',
        'data/client_by_category.xml',
        'data/client_by_vendor.xml',
        'data/client_by_price_point.xml',
        'data/client_birthday_list.xml',
        'data/vendor_sell_thru_internal.xml',
        'data/vendor_sell_thru_external.xml',
        'data/category_sell_thru_sku.xml',
        'views/account_report_view.xml',
        'views/report_template.xml',
        'views/report_menu_action.xml',
        'views/res_partner_view.xml',
        'views/gamification_goal_view.xml',
        'views/hr_employee_view.xml',
        'views/product_template_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bista_sale_reports/static/src/js/account_reports.js',
        ],
    },
    'installable': True,
    'application': True,
}
