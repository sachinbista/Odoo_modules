# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Pattern(models.Model):
	_name = "pattern"
	_description = "Pattern"
	
	name = fields.Char(string='Name')


class PatternFamily(models.Model):
	_name = "pattern.family"
	_description = "Pattern Family"
	
	name = fields.Char(string='Name')


class ColorName(models.Model):
	_name = "color.name"
	_description = "Color Name"
	
	name = fields.Char(string='Name')


class ColorFamily(models.Model):
	_name = "color.family"
	_description = "Color Family"
	
	name = fields.Char(string='Name')


class FabricContent(models.Model):
	_name = "fabric.content"
	_description = "Fabric Content"
	
	name = fields.Char(string='Name')


class Collection(models.Model):
	_name = "collection"
	_description = "Collection"
	
	name = fields.Char(string='Name')


class CleaningCode(models.Model):
	_name = "cleaning.code"
	_description = "Cleaning Code"
	
	name = fields.Char(string='Name')


class ProductTemplate(models.Model):
	_inherit = "product.template"
	
	s_cost_log = fields.One2many('product.cost.log', 's_product_tmpl_id',
	                             string="Product Cost Log")
	
	pattern_id = fields.Many2one('pattern', string="Pattern")
	pattern_family_id = fields.Many2one('pattern.family',
	                                    string="Pattern Family")
	
	color_name_id = fields.Many2one('color.name', string="Color Name")
	color_family_id = fields.Many2one('color.family', string="Color Family")
	
	base_cloth_id = fields.Many2one('product.template', string="Base Cloth")
	fabric_content_id = fields.Many2one('fabric.content',
	                                    string="Fabric Content")
	fabric_use_type = fields.Selection([('indoor', 'Indoor'),
	                                    ('outdoor', 'Outdoor')],
	                                   string="Fabric Use Type")
	uv_rating = fields.Integer(string="UV Rating")
	fabric_width = fields.Float(string="Fabric Width")
	fabric_weight = fields.Float(string="Fabric Weight")
	cleaning_code_id = fields.Many2one('cleaning.code', string="Cleaning Code")
	abrasion = fields.Integer(string="Abrasion", default=0)
	swatch_skus_id = fields.Many2one('product.template', string="Swatch SKUs")
	collection_ids = fields.Many2many(comodel_name='collection',
	                                  relation='collections_rel',
	                                  column1='colls1', column2='colls2',
	                                  string="Collections")
	# screen pp fields
	screen_pp1 = fields.Char(string="SCREEN_PP#_1")
	screen_pp2 = fields.Char(string="SCREEN_PP#_2")
	screen_pp3 = fields.Char(string="SCREEN_PP#_3")
	screen_pp4 = fields.Char(string="SCREEN_PP#_4")
	screen_pp5 = fields.Char(string="SCREEN_PP#_5")
	screen_pp6 = fields.Char(string="SCREEN_PP#_6")
	screen_pp7 = fields.Char(string="SCREEN_PP#_7")
	screen_pp8 = fields.Char(string="SCREEN_PP#_8")
	screen_pp9 = fields.Char(string="SCREEN_PP#_9")
	screen_pp10 = fields.Char(string="SCREEN_PP#_10")
	screen_pp11 = fields.Char(string="SCREEN_PP#_11")
	screen_pp12 = fields.Char(string="SCREEN_PP#_12")
	
	msrp = fields.Float('MSRP', default=1.0, digits='Product Price')
	horizontal_repeat = fields.Float(string="Horizontal repeat")
	vertical_repeat = fields.Float(string="Vertical Repeat")
	prod_long_desc = fields.Text(string="Product Long Description")
	is_export_stock = fields.Boolean(string="Is Export Stock?", default=False)
	product_export_ids = fields.One2many('product.export.stock.line',
	                                     'product_export_id',
	                                     string='Product Export Ids')
	upc = fields.Char(string='UPC')
	
	@api.onchange('base_cloth_id')
	def _onchange_template_base_cloth_id(self):
		if self.base_cloth_id:
			self.fabric_content_id = self.base_cloth_id.fabric_content_id
		else:
			self.fabric_content_id = False
	
	@api.depends('pattern_id', 'color_name_id', 'base_cloth_id',
	             'fabric_content_id', 'fabric_use_type',
	             'uv_rating', 'fabric_width', 'fabric_weight',
	             'cleaning_code_id', 'abrasion', 'swatch_skus_id',
	             'collection_ids', 'continuity_ids')
	def _compute_default_fabric_detail(self):
		unique_variants = self.filtered(
			lambda template: len(template.product_variant_ids) == 1)
		for template in unique_variants:
			template.default_code = template.product_variant_ids.default_code
			values = {
				'pattern_id': template.pattern_id,
				'color_name_id': template.color_name_id,
				'base_cloth_id': template.base_cloth_id,
				'fabric_content_id': template.fabric_content_id,
				'fabric_use_type': template.fabric_use_type,
				'uv_rating': template.uv_rating,
				'fabric_width': template.fabric_width,
				'fabric_weight': template.fabric_weight,
				'cleaning_code_id': template.cleaning_code_id,
				'abrasion': template.abrasion,
				'swatch_skus_id': template.swatch_skus_id,
				'collection_ids': template.collection_ids,
				'continuity_ids': template.continuity_ids,
				
			}
			template.product_variant_ids.write(values)
	
	def _set_default_fabric_detail(self):
		for template in self.filtered(
			lambda t: len(t.product_variant_ids) == 1):
			values = {
				'pattern_id': template.pattern_id,
				'color_name_id': template.color_name_id,
				'base_cloth_id': template.base_cloth_id,
				'fabric_content_id': template.fabric_content_id,
				'fabric_use_type': template.fabric_use_type,
				'uv_rating': template.uv_rating,
				'fabric_width': template.fabric_width,
				'fabric_weight': template.fabric_weight,
				'cleaning_code_id': template.cleaning_code_id,
				'abrasion': template.abrasion,
				'swatch_skus_id': template.swatch_skus_id,
				'collection_ids': template.collection_ids,
				'continuity_ids': template.continuity_ids,
			}
			template.product_variant_ids.write(values)
	
	@api.constrains('is_export_stock')
	def _check_export_stock(self):
		for record in self:
			existing_stock_product = self.env[
				'product.export.stock.line'].search(
				[('product_id', '=', record.product_variant_id.id)])
			if existing_stock_product:
				if (existing_stock_product.product_export_id.is_export_stock
					and record.is_export_stock):
					raise ValidationError(
						_('You cannot export stock for this product.'))
