# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ScrapLotWizard(models.TransientModel):
    _name = "scrap.lot.wizard"
    _description = "Scrap Lot Wizard"

    product_id = fields.Many2one('product.product', string="Product")
    lot_id = fields.Many2one('stock.lot', string="Lot")
    qty_available = fields.Integer(string="Quantity Available")
    scrap_location_id = fields.Many2one('stock.location', string="Scrap Location")
    lot_ids = fields.Many2many('stock.lot', 'scrap_lot_wiz_new', 'lot_id',
                               'scrap_lot_id', string="Lot IDs")
    def scrap(self):
        for rec in self:
            quant_ids = rec.product_id.stock_quant_ids.filtered(lambda l: l.lot_id == rec.lot_id)
            location_id = quant_ids.location_id.filtered(lambda l: l.usage == 'internal')
            scrap_vals = {
                'product_id': rec.product_id.id,
                'scrap_qty': rec.qty_available,
                'product_uom_id': rec.product_id.uom_id.id,
                'location_id': location_id.id,
                'scrap_location_id': rec.scrap_location_id.id,
                'origin': '',
                'lot_id': rec.lot_id.id
            }
            scrap_id = self.env['stock.scrap'].create(scrap_vals)
            scrap_id.action_validate()
            active_ids = self.lot_ids.ids
            action = self.env['ir.actions.act_window']._for_xml_id(
                'bista_zpl_labels.print_wizard_action')
            action['context'] = {
                'default_model': 'stock.lot',
                'default_lot_ids': [
                    (6, 0, active_ids)]}
            return action
