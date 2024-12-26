# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowCommonLogBook(models.Model):
    _name = 'goflow.common.log.book'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'GoFlow Connector Log Book'

    name = fields.Char(string='Name', required=True)
    type = fields.Selection([('	import', 'Import'), ('export', 'Export')], string='Opertaion')
    create_date = fields.Datetime(string='Created on')
    model_id = fields.Many2one(comodel_name='ir.model', string='Model')
    active = fields.Boolean(string='Active')
    res_id = fields.Integer(string='Record ID')
    log_lines = fields.One2many('goflow.common.log.lines', 'log_book_id', string='Log Lines')
