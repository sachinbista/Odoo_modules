# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrossDockRouteLine(models.Model):
    _name = 'cross.dock.route.line'
    _description = 'Cross Dock Route Line'
    _order = 'sequence, id'

    sequence = fields.Integer(
        required=True, index=True, default=1)
    transfer_type = fields.Selection([
        ('inter_company', 'Inter Company'),
        ('inter_warehouse', 'Inter Warehouse'),
    ], default='inter_company', string='Transfer Type')
    stock_transfer_id = fields.Many2one(
        'inter.company.stock.transfer')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.user.company_id)
    dest_company_id = fields.Many2one(
        'res.company', string='Destination Company')
    warehouse_id = fields.Many2one(
        'stock.warehouse', required=True)
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse', required=True,
        string='Destination Warehouse')

    @api.onchange('transfer_type')
    def onchange_transfer_type(self):
        self.dest_company_id = False
        self.dest_warehouse_id = False

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.warehouse_id = False
        if self.transfer_type == 'inter_company':
            if self.company_id and self.dest_company_id and \
                    self.company_id.id == self.dest_company_id.id:
                raise ValidationError(_(
                    'Source and Destination Company must '
                    'be different'))
        else:
            if self.company_id:
                self.dest_company_id = self.company_id.id

    @api.onchange('dest_company_id')
    def onchange_dest_company_id(self):
        self.dest_warehouse_id = False
        if self.transfer_type == 'inter_company':
            if self.company_id and self.dest_company_id and \
                    self.company_id.id == self.dest_company_id.id:
                raise ValidationError(_(
                    'Source and Destination Company must '
                    'be different'))

    @api.onchange('warehouse_id', 'dest_warehouse_id')
    def onchange_warehouse(self):
        if self.warehouse_id and self.dest_warehouse_id and \
                self.warehouse_id.id == self.dest_warehouse_id.id:
            raise ValidationError(_(
                'Source and Destination Warehouse '
                'must be different'))
