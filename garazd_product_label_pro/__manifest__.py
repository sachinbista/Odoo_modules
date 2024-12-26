# Copyright © 2022 Garazd Creation (https://garazd.biz)
# @author: Yurii Razumovskyi (support@garazd.biz)
# @author: Iryna Razumovska (support@garazd.biz)
# License OPL-1 (https://www.odoo.com/documentation/15.0/legal/licenses.html).

{
    'name': 'Odoo Product Label Builder',
    'version': '16.0.1.10.0',
    'category': 'Extra Tools',
    'author': 'Garazd Creation',
    'website': 'https://garazd.biz/en/shop/category/odoo-product-labels-15',
    'license': 'OPL-1',
    'summary': 'Product Barcode Label Building and Printing | Professional Tool to Print Labels | Barcode Product Label Builder | Product Label Designer | Sticker Label Maker | Dymo Label Maker | Barcode Label Generator | Direct Print',
    'images': ['static/description/banner.png', 'static/description/icon.png'],
    'live_test_url': 'https://garazd.biz/r/vnW',
    'depends': [
        'garazd_product_label',
        'garazd_product_label_print',
        'link_tracker',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/product_label_reports.xml',
        'report/product_label_templates.xml',
        'data/print_product_label_template_data.xml',
        'data/print_product_label_section_data.xml',
        'views/print_product_label_template_views.xml',
        'views/print_product_label_section_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/print_product_label_views.xml',
        'wizard/print_product_label_template_add_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/product_pricelist_demo.xml',
        'data/res_company_demo.xml',
    ],
    'price': 129.0,
    'currency': 'EUR',
    'support': 'support@garazd.biz',
    'application': True,
    'installable': True,
    'auto_install': False,
}
