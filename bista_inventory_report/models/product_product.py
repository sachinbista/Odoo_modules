# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = "product.product"
    _inherits = {'product.template': 'product_tmpl_id'}


    pattern_id = fields.Many2one('pattern', string="Pattern")
    pattern_family_id = fields.Many2one('pattern.family', string="Pattern Family")

    color_name_id = fields.Many2one('color.name', string="Color Name")
    color_family_id = fields.Many2one('color.family', string="Color Family")

    base_cloth_id = fields.Many2one('product.product', string="Base Cloth")
    fabric_content_id = fields.Many2one('fabric.content', string="Fabric Content")
    fabric_use_type = fields.Selection([('indoor', 'Indoor'),
                                        ('outdoor', 'Outdoor')], string="Fabric Use Type")
    uv_rating = fields.Integer(string="UV Rating")
    fabric_width = fields.Float(string="Fabric Width")
    fabric_weight = fields.Float(string="Fabric Weight")
    cleaning_code_id = fields.Many2one('cleaning.code', string="Cleaning Code")
    abrasion = fields.Integer(string="Abrasion",)
    swatch_skus_id = fields.Many2one('product.product', string="Swatch SKUs")
    collection_ids = fields.Many2many(comodel_name='collection', relation='collection_rel',
                                      column1='coll1', column2='coll2', string="Collections")
    horizontal_repeat = fields.Float(string="Horizontal repeat")
    vertical_repeat = fields.Float(string="Vertical Repeat")
    prod_long_desc = fields.Text(string="Product Long Description")

    # msrp = fields.Float('MSRP', default=1.0, digits='Product Price')

    @api.onchange('base_cloth_id')
    def _onchange_base_cloth_id(self):
        if self.base_cloth_id:
            self.fabric_content_id = self.base_cloth_id.fabric_content_id
        else:
            self.fabric_content_id = False
