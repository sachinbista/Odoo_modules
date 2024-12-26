# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class ProductCostLog(models.Model):
    _name = "product.cost.log"
    _inherit = 'mail.thread'

    s_old_cost = fields.Float(string="Old Standard Cost")
    s_new_cost = fields.Float(string="New Standard Cost")
    s_shippment_cost = fields.Float(string="Received Price")
    s_product_tmpl_id = fields.Many2one('product.template', string='Product')
    s_user_id = fields.Many2one('res.users', string='Users')
    s_product_qty_available = fields.Float(string="QTY Available", related="s_product_tmpl_id.qty_available")
