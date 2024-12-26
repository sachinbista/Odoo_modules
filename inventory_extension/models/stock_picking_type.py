# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _get_barcode_config(self):
        self.ensure_one()
        config = super(StockPickingType, self)._get_barcode_config()
        # Defines if all lines need to be packed to be able to validate a transfer.
        if (config and 'lines_need_to_be_packed' in config and self.code ==
                'outgoing'):
            config.update({
                'skip_validate': True
            })
        return config


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In progress'),
        ('picked', 'Picked'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='draft',
        store=True, compute='_compute_state',
        copy=False, tracking=True, required=True, readonly=True, index=True)

    def action_done(self):
        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
            self.write({'state': 'picked'})
            return True
        return super(StockPickingBatch, self).action_done()

    @api.model
    def default_get(self, fields):
        res = super(StockPickingBatch, self).default_get(fields)
        if 'picking_type_id' in res:
            res.update({'picking_type_id': False})
        return res


