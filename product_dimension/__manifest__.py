# Copyright 2018 brain-tec AG (http://www.braintec-group.com)
# Copyright 2015-2016 Camptocamp SA
# Copyright 2015 ADHOC SA  (http://www.adhoc.com.ar)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Product Dimension",
    "version": "16.0.1.1.0",
    "category": "Product",
    "author": "brain-tec AG, ADHOC SA, Camptocamp SA, "
    "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/product-attribute",
    "depends": ["product","stock"],
    "data": [
        "views/product_view.xml",
        "views/stock_location.xml"
    ],
    "installable": True,
    "images": ["static/description/icon.png"],
}
