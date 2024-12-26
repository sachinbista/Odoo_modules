# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowCommonLogLines(models.Model):
    _name = 'goflow.common.log.lines'
    _description = 'GoFlow Connector Log Lines'

    instance_id = fields.Many2one(comodel_name='goflow.configuration',
                                  string='Instances')
    picking_id = fields.Many2one(comodel_name='stock.picking',string='Transfer')
    move_id = fields.Many2one(comodel_name='account.move',string='Invoice')
    product_id = fields.Many2one(comodel_name='product.product',string='Product')
    product_id = fields.Many2one(comodel_name='product.product',string='Product')
    log_book_id = fields.Many2one(comodel_name='goflow.common.log.book',string='Log Book')
    model_id = fields.Many2one(comodel_name='ir.model',string='Model')
    order_ref = fields.Char(string='Order Reference')
    default_code = fields.Char(string='SKU')
    message = fields.Text(string='Message')
    res_id = fields.Integer(string='Record ID')

