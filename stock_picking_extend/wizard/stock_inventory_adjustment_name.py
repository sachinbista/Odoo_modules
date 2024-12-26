# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockInventoryAdjustmentName(models.TransientModel):
    _inherit = 'stock.inventory.adjustment.name'

    def manager_pin(self):
        return {
                'name': 'Authentication Pin',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'quant.pin.check.wiz',
                'view_id': self.env.ref('stock_picking_extend.quant_pin_check_wiz_form_view').id,
                'target': 'new',
                'context': {'default_quant_ids': self.quant_ids.ids, 'default_show_info': self.show_info},
            }

    def action_apply(self):
        if not 'approval_process' in self._context:
            return self.manager_pin()
        return super(StockInventoryAdjustmentName, self).action_apply()

    

    
