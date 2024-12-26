# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class SplitLotWizard(models.TransientModel):
    _name = "split.lot.wizard"
    _description = "Split Lot Wizard"

    product_id = fields.Many2one('product.product', string="Product",
                                 domain="[('categ_id.auto_lot_generation', '=', True),('detailed_type', '=', 'product'), ('tracking', '=', 'lot')]")
    lot_id = fields.Many2one('stock.lot', string="Lot")
    quantity = fields.Integer(string="Quantity", compute="compute_quantity", store=True)
    dest_location_id = fields.Many2one('stock.location', string="Destination Location",
                                       domain=[('usage', '=', 'internal')])
    split_lot_ids = fields.One2many('split.lot.line.wizard', 'split_id', string="Split Lot Ids")
    qty_available = fields.Integer(string="Quantity Available", compute="compute_qty_available", store=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        lots = self.env['stock.lot'].search([('product_id', '=', self.product_id.id)])
        lot_lst = []
        for lot in lots:
            if lot.product_qty > 0.0:
                lot_lst.append(lot.id)
        self.lot_id = False
        if self.product_id:
            return {'domain': {'lot_id': [('id', 'in', lot_lst)]}}
        else:
            return {'domain': {'lot_id': [('id', 'in', lot_lst)]}}

    @api.depends('lot_id')
    def compute_quantity(self):
        self.quantity = self.lot_id.product_qty

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        self.qty_available = self.lot_id.product_qty

    @api.depends('split_lot_ids.total_quantity')
    def compute_qty_available(self):
        for rec in self:
            total_lot_quantity = sum(line.total_quantity for line in rec.split_lot_ids)
            rec.qty_available = rec.quantity - total_lot_quantity

    def split_lot(self):
        new_lot_lst = []
        if self.lot_id and self.quantity > 0:
            total_lot_quantity = sum(rec.lot_quantity * rec.multiple for rec in self.split_lot_ids)

            if total_lot_quantity > self.quantity:
                raise ValidationError("Total lot quantity exceeds the available quantity.")

            for rec in self.split_lot_ids:
                if rec.lot_quantity <= 0 or rec.multiple <= 0:
                    continue

                total_quantity = rec.lot_quantity * rec.multiple
                if total_quantity <= 0:
                    continue

                # Create new lots and adjust the quantity of the selected lot
                selected_lot = rec.split_id.lot_id
                for quant in selected_lot.quant_ids:
                    if quant.location_id.usage == 'internal':
                        quant.write({'quantity': selected_lot.product_qty - total_quantity})
                        quant.sudo()._compute_inventory_quantity_auto_apply()
                new_quant_ids = []
                for i in range(rec.multiple):
                    quant_vals = ({
                        'product_id': selected_lot.product_id.id,
                        'product_qty': rec.lot_quantity,
                        'location_id': self.dest_location_id.id,
                    })
                    lot_id = self.env['stock.lot'].with_context(inventory_mode=True).create(quant_vals)
                    new_lot_lst.append(lot_id.id)
                    inv_adj_vals = ({'product_id': selected_lot.product_id.id,
                                     'inventory_quantity': rec.lot_quantity,
                                     'lot_id': lot_id.id,
                                     'location_id': self.dest_location_id.id,
                                     })
                    new_quant = self.env['stock.quant'].create(inv_adj_vals)
                    new_quant.sudo().action_apply_inventory()
                    new_quant_ids.append(new_quant)
                if rec.is_scrap_line:
                    quant_ids = new_quant_ids
                    for quant in new_quant_ids:
                        location_id = quant.location_id.filtered(lambda l: l.usage == 'internal')
                        scrap_vals = {
                            'product_id': rec.split_id.product_id.id,
                            'scrap_qty': quant.quantity,
                            'product_uom_id': rec.split_id.product_id.uom_id.id,
                            'location_id': location_id.id,
                            'scrap_location_id': rec.split_lot_scrap_location_id.id,
                            'origin': '',
                            'lot_id': quant.lot_id.id
                        }
                        scrap_id = self.env['stock.scrap'].create(scrap_vals)
                        scrap_id.action_validate()
            if self.qty_available > 0:
                view_id = self.env['ir.ui.view'].search([('name', '=', 'ask_scrap_wizard')])

                # Create an action for the wizard
                action = {
                    'name': "Split Rolls Scrap",
                    'type': 'ir.actions.act_window',
                    'res_model': 'ask.scrap.wizard',
                    'view_mode': 'form',
                    'view_id': view_id.id,
                    'target': 'new',
                    'context': {
                        'default_product_id': self.product_id.id,
                        'default_lot_id': self.lot_id.id,
                        'default_qty_available': self.qty_available,
                        'default_lot_ids': [(4, lot) for lot in new_lot_lst]
                        },
                }
                return action
            else:
                active_ids = new_lot_lst
                action = self.env['ir.actions.act_window']._for_xml_id(
                    'bista_zpl_labels.print_wizard_action')
                action['context'] = {
                    'default_model': 'stock.lot',
                    'default_lot_ids': [
                        (6, 0, active_ids)]}
                return action


class SplitLotLineWizard(models.TransientModel):
    _name = "split.lot.line.wizard"

    split_id = fields.Many2one('split.lot.wizard', string="Split Id")
    lot_quantity = fields.Integer(string="Lot Quantity")
    multiple = fields.Integer(string="Multiple")
    total_quantity = fields.Integer(string="Total Quantity", compute="compute_lot_quantity",
        store=True)
    split_lot_scrap_location_id = fields.Many2one('stock.location', string="Scrap Location")
    is_scrap_line = fields.Boolean(string="Is Scrap Line")

    @api.depends('lot_quantity', 'multiple')
    def compute_lot_quantity(self):
        for rec in self:
            rec.total_quantity = rec.lot_quantity * rec.multiple
