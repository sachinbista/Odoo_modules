# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_image_360_ids = fields.One2many('product.image.360', 'product_tmpl_id', string='Images')
    display_360_image = fields.Boolean(string='Display 360 Image')


class ProductImage360(models.Model):
    _name = 'product.image.360'
    _description = "Product Image 360"
    _order = 'sequance'

    name = fields.Char(string='Name')
    image = fields.Binary(string='Image', attachment=True)
    image_filename = fields.Char()
    product_tmpl_id = fields.Many2one('product.template', string='Related Product', copy=True)
    sequance = fields.Integer(string="Sequance")
    production_lot_id = fields.Many2one('stock.production.lot', string='Related Product Lot', copy=True)
    image_s3_url = fields.Char(string='Image URL')
