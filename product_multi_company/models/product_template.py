# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = ["multi.company.abstract", "product.template"]
    _name = "product.template"

    status = fields.Selection([('active', 'Active'), ('discontinued', 'Discontinued')],
                              string='Status', default='active')

    barcode = fields.Char('UPC', compute='_compute_barcode', inverse='_set_barcode',
                          search='_search_barcode',
                          required=True)
    default_code = fields.Char(
        'SKU', compute='_compute_default_code',
        inverse='_set_default_code', store=True, required=True)
    product_display_name = fields.Char(string="Product Display Name",tracking=True)
    product_display_name_40 = fields.Char(string="Product Display Name - 40 Character",size=40)
    product_display_name_30 = fields.Char(string="Product Display Name - 30 Character",size=30)
    product_display_name_36 = fields.Char(string="Product Display Name - 36 Character",size=36)
    product_display_name_20 = fields.Char(string="Product Display Name - 20 Character",size=20)
    product_display_name_short = fields.Char(string="Product Display Name - Shortened")
    product_sub_categ_1 = fields.Many2one('product.sub.category.a', string='Product Sub-Category 1')
    product_sub_categ_2 = fields.Many2one('product.sub.category.b', string='Product Sub-Category 2')
    is_gift = fields.Boolean(string='Gift With Purchase / Not for Individual Sale')
    product_group_id = fields.Many2one('product.group', string='Product Group',tracking=True)
    product_group_id_cartons = fields.Many2one('product.group.carton', string='Product Group - Cartons',tracking=True)
    color_name = fields.Char(string='Color Name',tracking=True)
    facet_color = fields.Char(string='Facet Color')
    hex_code = fields.Char(string='Hex Code',tracking=True)
    is_hypoallergenic_color = fields.Boolean(string='Hypoallergenic Colour Flag',tracking=True)
    size = fields.Many2one('product.size', string='Size',tracking=True)
    count_items = fields.Integer(string='Count Items')
    includes = fields.Char(string='Includes')
    release_id = fields.Many2one('product.release', string='Release',tracking=True)
    collection_id = fields.Many2one('product.collection', string='Collection / Season / Range',tracking=True)
    exclusivity_ids = fields.Many2many('product.exclusivity', string='Exclusivity',tracking=True)
    production_edition = fields.Selection([('core', 'Core'), ('limited', 'Limited Edition')], string='Core / Limited Edition',tracking=True)
    # region_availability_ids = fields.Many2many('res.country','template_country_rel',
    #                                            'template_id','country_id',
    #                                            string='Region Availability',tracking=True)
    ats_date = fields.Date(string='ATS Date',tracking=True)
    wholesale_launch_date = fields.Date(string='Wholesale Launch Date')
    slip_ecomm_launch_date = fields.Date(string='Slip Ecomm Launch Date')
    global_discontinued_date = fields.Date(string='Global Discontinued Date')
    what_is_it = fields.Char(string='What Is It? - 150 character limit',size=150)
    how_to_use = fields.Char(string='How To Use')
    how_to_use_shortended = fields.Char(string='How To Use - Shortened')
    recommended = fields.Char(string='Recommended / Suitable For')
    benifits = fields.Char(string='Benefits / Features')
    romance_copy = fields.Char(string='Romance Copy*')
    key_ingredients = fields.Char(string='Key Ingredients')
    full_ingredients = fields.Char(string='Full Ingredients')
    care_instructions = fields.Char(string='Care Instructions')
    awards = fields.Char(string='Awards')
    retailer_ids = fields.Many2many('product.template.retailer','product_template_retailer_rel',
                                    'template_id',
                                    'retailer_id',
                                    string="Retailer")
