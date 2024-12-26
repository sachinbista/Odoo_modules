# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # def button_validate(self):
    #     for rec in self:
    #         if rec.picking_type_id.is_package and not self.env.context.get('package') and not rec.move_line_ids.result_package_id:
    #             view_id = self.env.ref('bista_remove_merge_move.view_package_wizard_form').id
    #             return {
    #                 'name': 'Validate Package',
    #                 'type': 'ir.actions.act_window',
    #                 'res_model': 'package.wizard',
    #                 'view_mode': 'form',
    #                 'view_id': view_id,
    #                 'views': [[view_id, 'form']],
    #                 'target': 'new',
    #                 'context': {'active_id': rec.id},
    #             }
    #
    #     return super(StockPicking, self).button_validate()

    def _pre_action_done_hook(self):
        for rec in self:
            if rec.picking_type_id.is_package and not self.env.context.get('package') and not rec.move_line_ids.result_package_id:
                view_id = self.env.ref('bista_remove_merge_move.view_package_wizard_form').id
                return {
                    'name': 'Validate Package',
                    'type': 'ir.actions.act_window',
                    'res_model': 'package.wizard',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'views': [[view_id, 'form']],
                    'target': 'new',
                    'context': {'active_id': rec.id},
                }
        res = super()._pre_action_done_hook()
        return res

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        if self.picking_type_id.code == 'outgoing' and not self.picking_type_id.is_subcontractor:
            # Search for stock.quant.package records with matching sale_order_id
            matching_packages = self.env['stock.quant.package'].search([
                ('sale_order_id', '=', self.sale_id.id)])

            if matching_packages:
                # Unlink all related data in matching_packages
                for package in matching_packages:
                    package.unpack()
                    # package.sale_order_id = False
                    # package.customer_id = False
                    # package.location_id = False
                    # package.company_id = False
                    # package.pack_date = False
                    # for quant in package.quant_ids:
                    #     package.quant_ids = [(3, quant.id)]
        return res
