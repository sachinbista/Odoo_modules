# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, models, fields, _
import logging

_logger = logging.getLogger(__name__)


class RithumProductProduct(models.Model):
    _name = 'rithum.product.product'
    _rec_name = 'product_id'
    _description = "Rithum Product Variant"

    product_id = fields.Many2one('product.product', 'Order Product', copy=False, required=1)
    inventory_product_id = fields.Many2one('product.product', 'Inventory Product', copy=False)
    product_default_code = fields.Char('Odoo Handle Sku', related='product_id.default_code')
    rithum_product_id = fields.Char('Rithum Product', copy=False)
    rithum_map_error = fields.Text('Map Error', copy=False)
    rithum_config_id = fields.Many2one('rithum.config', string="Rithum Config ID",
                                       default=lambda self: self.env['rithum.config'].search([]), limit=1)
    active = fields.Boolean('Active', default=True)