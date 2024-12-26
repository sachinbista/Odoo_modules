# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class AskScrapWizard(models.TransientModel):
    _name = "ask.scrap.wizard"
    _description = "Ask Scrap Wizard"

    product_id = fields.Many2one('product.product', string="Product")
    lot_id = fields.Many2one('stock.lot', string="Lot")
    qty_available = fields.Integer(string="Quantity Available")

    def yes(self):
        view_id = self.env['ir.ui.view'].search([('name', '=', 'scrap_lot_wizard')])

        # Create an action for the wizard
        action = {
            'name': "Scrap Reminder",
            'type': 'ir.actions.act_window',
            'res_model': 'scrap.lot.wizard',
            'view_mode': 'form',
            'view_id': view_id.id,
            'target': 'new',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot_id': self.lot_id.id,
                'default_qty_available': self.qty_available},
        }

        return action

    def cancel(self):
        active_ids = self.lot_ids.ids
        action = self.env['ir.actions.act_window']._for_xml_id(
            'bista_zpl_labels.print_wizard_action')
        action['context'] = {
            'default_model': 'stock.lot',
            'default_lot_ids': [
                (6, 0, active_ids)]}
        return action

