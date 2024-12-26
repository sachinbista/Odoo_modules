# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_default_warehouse = fields.Boolean(string="Default Warehouse")

    @api.constrains('is_default_warehouse')
    def _check_default_warehouse(self):
        for rec in self:
            if rec.is_default_warehouse and len(rec.env['stock.warehouse'].search(
                    [('company_id', '=', rec.company_id.id), ('is_default_warehouse', '=', True)])) > 1:
                raise ValidationError(_("Every Warehouse can only have 1 default warehouse!"))

    @api.model_create_multi
    def create(self, vals_list):
        context = self.env.context
        for vals in vals_list:
            if context.get('goflow_warehouse'):
                seq_date = fields.Datetime.now()
                vals['code'] = self.env['ir.sequence'].next_by_code('stock.warehouse', sequence_date=seq_date)
        return super().create(vals_list)
