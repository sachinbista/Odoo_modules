# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    package_id = fields.Many2one('stock.quant.package', string="Package")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Functions create package, links it to the respect MO.
        """
        res = super(MrpProduction, self).create(vals_list)
        sale_order_id = res.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
        for rec in res:
            if rec.product_id.is_package:
                package_sequence = self.env['ir.sequence'].next_by_code(
                    'stock.quant.package')
                today = fields.Datetime.now()
                package = self.env['stock.quant.package'].create({
                    'name': package_sequence,
                    'location_id': rec.location_dest_id.id,
                    'sale_order_id': sale_order_id.id,
                    'customer_id': sale_order_id.partner_id.id,
                    'mo_id': rec.id
                })
                rec.write({'package_id': package.id})
        return res

    def button_mark_done(self):
        """
        Function links products to respected package on the confirmation of MO.
        """
        res = super(MrpProduction, self).button_mark_done()
        sale_order_id = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
        for rec in self:
            for move_lines in rec.finished_move_line_ids:
                package = self.env['stock.quant.package'].search([('mo_id', '=', rec.id)])
                if package:
                    move_lines.write({'result_package_id': package.id})
        return res

    def action_open_product_package(self):
        package = self.env['stock.quant.package'].search([('mo_id', '=', self.id)], limit=1)
        if package:
            return {
                'name': 'Package',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.quant.package',
                'res_id': package.id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
                'context': self._context,
            }
