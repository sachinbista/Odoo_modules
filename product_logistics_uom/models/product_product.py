# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    height = fields.Float(string="Height")
    width = fields.Float(string="Width")
    length = fields.Float(string="Length")
