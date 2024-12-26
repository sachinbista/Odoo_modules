# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################

from odoo import fields,api,models
import base64
import urllib
import requests
from PIL import Image
from io import BytesIO

class ProductImportSolution(models.Model):
    _name = 'product.import.solution'
    _description = 'Products Import Solution'

    name = fields.Char(string='Product Name')
    code = fields.Char(string='Vendor Code')
    item_id = fields.Char(string='Item ID')
    description = fields.Text(string='Product Description')

    default_image = fields.Binary(string='Default Image',compute='load_image')

    image_url_1 = fields.Char(string='Image 1')
    image_url_2 = fields.Char(string='Image 2')
    image_url_3 = fields.Char(string='Image 3')
    image_url_4 = fields.Char(string='Image 4')
    image_url_5 = fields.Char(string='Image 5')
    image_url_6 = fields.Char(string='Image 6')

    price = fields.Float(string='Price')

    vendor = fields.Many2one(comodel_name='res.partner',string='Vendor')
    product_category = fields.Many2one(comodel_name='product.category',string='Product Category')

    brand = fields.Many2one(comodel_name='product.brand',string='Brand')
    family = fields.Many2one(comodel_name='product.brand.family',string='Family')
    pos_categ_id = fields.Many2one(comodel_name='pos.category',string='Pos Category')

    variant_1 = fields.Char(string='Attribute Value 1')
    variant_2 = fields.Char(string='Attribute Value 2')
    variant_3 = fields.Char(string='Attribute Value 3')
    variant_4 = fields.Char(string='Attribute Value 4')
    variant_5 = fields.Char(string='Attribute Value 5')
    variant_6 = fields.Char(string='Attribute Value 6')

    mapped_attr_1 = fields.Many2one(comodel_name='product.attribute',string='Mapped Attr 1',compute='get_mapped_attrs')
    mapped_attr_val_1 = fields.Many2one(comodel_name='product.attribute.value',string='Mapped Attr Val 1',compute='get_mapped_attrs')

    mapped_attr_2 = fields.Many2one(comodel_name='product.attribute',string='Mapped Attr 2',compute='get_mapped_attrs')
    mapped_attr_val_2 = fields.Many2one(comodel_name='product.attribute.value',string='Mapped Attr Val 2',compute='get_mapped_attrs')

    mapped_attr_3 = fields.Many2one(comodel_name='product.attribute',string='Mapped Attr 3',compute='get_mapped_attrs')
    mapped_attr_val_3 = fields.Many2one(comodel_name='product.attribute.value',string='Mapped Attr Val 3',compute='get_mapped_attrs')

    mapped_attr_4 = fields.Many2one(comodel_name='product.attribute',string='Mapped Attr 4',compute='get_mapped_attrs')
    mapped_attr_val_4 = fields.Many2one(comodel_name='product.attribute.value',string='Mapped Attr Val 4',compute='get_mapped_attrs')

    mapped_attr_5 = fields.Many2one(comodel_name='product.attribute',string='Mapped Attr 5',compute='get_mapped_attrs')
    mapped_attr_val_5 = fields.Many2one(comodel_name='product.attribute.value',string='Mapped Attr Val 5',compute='get_mapped_attrs')

    mapped_attr_6 = fields.Many2one(comodel_name='product.attribute',string='Mapped Attr 6',compute='get_mapped_attrs')
    mapped_attr_val_6 = fields.Many2one(comodel_name='product.attribute.value',string='Mapped Attr Val 6',compute='get_mapped_attrs')


    product_tmpl_id = fields.Many2one(comodel_name='product.template',string='Attached Template')
    product_variant_id = fields.Many2one(comodel_name='product.product',string='Attached Variant')

    state = fields.Selection([('draft', 'Draft'),('imported', 'Imported'),('error','Error')],string="Status", default='draft')
    notes = fields.Char(string='Notes')

    # @api.multi
    def get_mapped_attrs(self):
        for mapped_attrs in self:
            if mapped_attrs.variant_1 :
                res = self.env['mapped.product.attribute.lines'].search([('vendor', '=', mapped_attrs.vendor.id),('name','=',mapped_attrs.variant_1)],limit=1)
                mapped_attrs.mapped_attr_1 = res[0].mapped_attribute.id
                mapped_attrs.mapped_attr_val_1 = res[0].mapped_value.id

            if mapped_attrs.variant_2 :
                res = self.env['mapped.product.attribute.lines'].search([('vendor', '=', mapped_attrs.vendor.id),('name','=',mapped_attrs.variant_2)],limit=1)
                mapped_attrs.mapped_attr_2 = res[0].mapped_attribute.id
                mapped_attrs.mapped_attr_val_2 = res[0].mapped_value.id

            if mapped_attrs.variant_3 :
                res = self.env['mapped.product.attribute.lines'].search([('vendor', '=', mapped_attrs.vendor.id),('name','=',mapped_attrs.variant_3)],limit=1)
                mapped_attrs.mapped_attr_3 = res[0].mapped_attribute.id
                mapped_attrs.mapped_attr_val_3 = res[0].mapped_value.id

            if mapped_attrs.variant_4 :
                res = self.env['mapped.product.attribute.lines'].search([('vendor', '=', mapped_attrs.vendor.id),('name','=',mapped_attrs.variant_4)],limit=1)
                mapped_attrs.mapped_attr_4 = res[0].mapped_attribute.id
                mapped_attrs.mapped_attr_val_4 = res[0].mapped_value.id

            if mapped_attrs.variant_5 :
                res = self.env['mapped.product.attribute.lines'].search([('vendor', '=', mapped_attrs.vendor.id),('name','=',mapped_attrs.variant_5)],limit=1)
                mapped_attrs.mapped_attr_5 = res[0].mapped_attribute.id
                mapped_attrs.mapped_attr_val_5 = res[0].mapped_value.id

            if mapped_attrs.variant_6 :
                res = self.env['mapped.product.attribute.lines'].search([('vendor', '=', mapped_attrs.vendor.id),('name','=',mapped_attrs.variant_6)],limit=1)
                mapped_attrs.mapped_attr_6 = res[0].mapped_attribute.id
                mapped_attrs.mapped_attr_val_6 = res[0].mapped_value.id

    @api.depends('image_url_1')
    def load_image(self):
        for rec in self:
            rec.default_image = self.update_image(rec.image_url_1)


    # @api.multi
    def update_image(self,ONE_URL):
        r = requests.get(ONE_URL)
        Image.open(BytesIO(r.content))
        profile_image = base64.encodestring(urllib.request.urlopen(ONE_URL).read())
        return profile_image

class MappedAttributesAndValuesLines(models.Model):
    _name = 'mapped.product.attribute.lines'
    _description = 'Mapped Products Attributes'

    name = fields.Char(string='Original Attribute Value')
    vendor = fields.Many2one(comodel_name='res.partner', string='Vendors')
    mapped_value = fields.Many2one(comodel_name='product.attribute.value',string='Attribute Value')
    mapped_attribute = fields.Many2one(string='Map to', comodel_name='product.attribute')

