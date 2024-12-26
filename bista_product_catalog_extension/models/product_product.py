
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _,tools


class ProductProduct(models.Model):
    _inherit = 'product.product'

    catalog_prd_quantity = fields.Float(string="Quantity")
