# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _description = "Product Template"

    continuity_ids = fields.One2many('partner.product.relation', 'product_template_id', string="Continuity")


class ProductProduct(models.Model):
    _inherit = "product.product"
    _description = "Product Product"

    continuity_ids = fields.One2many('partner.product.relation', 'product_id', string="Continuity")


class PartnerProductRelation(models.Model):
    _name = "partner.product.relation"
    _description = "Partner Product Relation"

    date = fields.Date(string='Date')
    contact_id = fields.Many2one('res.partner', string='Contact')
    product_template_id = fields.Many2one('product.template', string="Product Template")
    product_id = fields.Many2one('product.product', string="Product Product")
