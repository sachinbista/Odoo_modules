# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, tools, _, _lt, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        for move in self.move_ids.filtered(lambda s: s.purchase_line_id):
                picking_id = move.picking_id.filtered(lambda s: s.picking_type_id.code=='incoming')
                landed_cost = self.env['stock.landed.cost'].sudo().search([('po_ids','=',move.purchase_line_id.order_id.id),('state','=','confirmed'),('target_model','=','purchase')])
                if picking_id.container_id:
                    for landed_cost_data in landed_cost.filtered(lambda s: s.container_id == picking_id.container_id):
                        landed_cost_data.update({
                            'picking_ids':[fields.Command.link(picking_id.id)],
                            })
                        landed_cost_data.button_validate()
                else:
                    for landed_cost_data in landed_cost:
                        landed_cost_data.update({
                        'picking_ids':[fields.Command.link(picking_id.id)],
                        })
                        landed_cost_data.button_validate()
        return super(StockPicking, self)._action_done()
    def button_validate(self):
        for move in self.move_ids.filtered(lambda s: s.purchase_line_id and s.picking_id.container_id):
            picking_id = move.picking_id.filtered(lambda s: s.picking_type_id.code=='incoming')
            landed_cost = self.env['stock.landed.cost'].sudo().search([('po_ids','=',move.purchase_line_id.order_id.id),('state','=','confirmed'),('target_model','=','purchase')])
            if not landed_cost and picking_id.picking_type_id.code =='incoming' and move.product_id.categ_id.property_cost_method !='standard':
                return self._action_generate_landedcost_Warning()
        return super().button_validate()
        


    def _action_generate_landedcost_Warning(self):
        view = self.env.ref('bista_landed_costs.landed_cost_warning_wizard')
        description=f"Please Create Landed Cost For Container is : {self.container_id}"
        return {
            'name': _('To Create Landed Cost ?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'landedcost.warning',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_description=description, default_pick_ids=[(4, p.id) for p in self]),
            }