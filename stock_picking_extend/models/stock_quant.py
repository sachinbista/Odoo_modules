# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def action_view_inventory(self):
        rec = super(StockQuant, self).action_view_inventory()
        add_new_filter = {'search_default_available_stock': 1}
        rec['context'].update(add_new_filter)
        return rec
	
    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        action = super(StockQuant, self)._get_quants_action(domain=None, extend=False)
        add_new_filter = {'search_default_available_stock': 1}
        action['context'].update(add_new_filter)
        return action

    def manager_pin(self, pin_for):
        return {
                'name': 'Authentication Pin',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'quant.pin.check.wiz',
                'view_id': self.env.ref('stock_picking_extend.quant_pin_check_wiz_form_view').id,
                'target': 'new',
                'context': {'pin_for': pin_for},
            }

    def action_set_inventory_quantity(self):
        for quant in self: 
            if not 'approval_process' in self._context:
                return quant.manager_pin('set_inventory')
        return super(StockQuant, self).action_set_inventory_quantity()

    def action_apply_inventory(self):
        for quant in self: 
            if not 'approval_process' in self._context:
                return quant.manager_pin('apply_inventory')
        return super(StockQuant, self).action_apply_inventory()

    # def action_set_inventory_quantity_to_zero(self):
    #     for quant in self: 
    #         if not 'approval_process' in self._context:
    #             return quant.manager_pin('set_zero')
    #     return super(StockQuant, self).action_set_inventory_quantity_to_zero()

    # def action_inventory_history(self):
    #     for quant in self: 
    #         if not 'approval_process' in self._context:
    #             return quant.manager_pin('set_history')
    #     return super(StockQuant, self).action_inventory_history()



		