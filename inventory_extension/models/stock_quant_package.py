# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class QuantPackage(models.Model):
    _inherit = "stock.quant.package"

    picking_id = fields.Many2one('stock.picking', string='Transfer')
    pack_count = fields.Integer("Pack Count")


class Picking(models.Model):
    _inherit = "stock.picking"

    def _put_in_pack(self, move_line_ids):
        package = super(Picking, self)._put_in_pack(move_line_ids)
        packages = self.env['stock.quant.package'].search(
            [('picking_id', '=', self.id)])
        max_count = max(packages.mapped('pack_count')) if packages else 0
        package.pack_count = max_count + 1
        return package

    # def button_validate(self):
    #     if not self._context.get('shopify_picking_validate'):
    #         for picking in self.filtered(lambda p:
    #                                      p.picking_type_id.code == 'outgoing'):
    #             quantity_move_line_ids = picking.move_line_ids.filtered(
    #                 lambda ml: not ml.result_package_id)
    #             if quantity_move_line_ids:
    #                 raise ValidationError(
    #                     _("Please put all products in the Pack."))
    #     return super(Picking, self).button_validate()

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model
    def update_picked_after_validate_delivery(self, ids_list):
        records = self.search([('id', 'in', ids_list)])

        for record in records:
            record.write({'picked': True})
