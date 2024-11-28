# Copyright 2023 Karthik <karthik@sodexis.com>
# Copyright 2020 Kevin Graveman <k.graveman@onestein.nl>
# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    company_ids = fields.Many2many(
        comodel_name="res.company",
        column1="product_id",
        column2="company_id",
        relation="product_product_company_rel",
        related="product_tmpl_id.company_ids",
        compute_sudo=True,
        readonly=False,
        store=True,
    )

    status = fields.Selection([('active', 'Active'), ('discontinued', 'Discontinued')],
                              string='Status',
                              tracking=True,
                              default='active')
    barcode = fields.Char(
        'UPC', copy=False, index='btree_not_null',
        help="International Article Number used for product identification.")
    default_code = fields.Char('SKU', index=True,tracking=True,size=30)
    product_display_name = fields.Char(string="Product Display Name")
    product_display_name_40 = fields.Char(string="Product Display Name - 40 Character", size=40)
    product_display_name_30 = fields.Char(string="Product Display Name - 30 Character", size=30)
    product_display_name_36 = fields.Char(string="Product Display Name - 36 Character", size=36)
    product_display_name_20 = fields.Char(string="Product Display Name - 20 Character", size=20)
    product_display_name_short = fields.Char(string="Product Display Name - Shortened")