# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_rithum_qty_changed = fields.Boolean(string="Rithum Quantity Changed", copy=False)