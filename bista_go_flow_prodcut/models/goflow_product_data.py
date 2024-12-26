# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowProductData(models.Model):
    _name = 'goflow.product.data'
    # _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Goflow Product Downloaded Data'

    item_number = fields.Char(string='Goflow Product Item No')
    name = fields.Char(string='Goflow Product Name')
    instance_id = fields.Many2one(comodel_name='goflow.configuration', string='Instance')
    external_id = fields.Integer(string='Goflow Product ID')
    goflow_product_data_line = fields.Text(string='Goflow product Downloaded Data')