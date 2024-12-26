# -*- encoding: utf-8 -*-

{
    "name": "Product logistics UoM",
    "summary": "Configure product weights and volume UoM",
    "version": "17.0.3.0.0",
    "development_status": "Beta",
    "category": "Product",
    'website': 'https://www.bistasolutions.com',
    'author': 'Bista Solutions Pvt. Ltd.',
    "maintainers": ["hparfr"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "product",
    ],
    "data": [
        "views/res_config_settings.xml",
        "views/product.xml",
    ],
}
