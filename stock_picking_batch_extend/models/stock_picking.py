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

    container_id = fields.Char(string="Container ID")
    date_etd = fields.Date(string="ETD")
    date_eta = fields.Date(string="ETA")
    batch_details = fields.Char(string="Batch")

    def button_validate(self):
        res = super().button_validate()
        if self.picking_type_id.batch_only_assigned:
            for picking in self:
                second_picking_id = self.env['stock.picking'].search(
                    [('origin', '=', picking.origin), ('id', '!=', picking.id)], limit=1,order='id')
                if second_picking_id:
                    second_picking_id._find_auto_batch()
        return res

    def _find_auto_batch(self):
        if self.picking_type_id.batch_only_assigned:
            if self.state == 'assigned':
                self.ensure_one()
                # Check if auto_batch is enabled for this picking.
                if not self.picking_type_id.auto_batch or self.immediate_transfer or self.batch_id or not self.move_ids or not self._is_auto_batchable():
                    return False

                if self.picking_type_id.batch_group_by_container and self.container_id == False:
                    return False

                # Try to find a compatible batch to insert the picking
                possible_batches = self.env['stock.picking.batch'].sudo().search(self._get_possible_batches_domain())
                for batch in possible_batches:
                    if batch._is_picking_auto_mergeable(self):
                        batch.picking_ids |= self
                        return batch

                # If no batch were found, try to find a compatible picking and put them both in a new batch.
                possible_pickings = self.env['stock.picking'].search(self._get_possible_pickings_domain())
                for picking in possible_pickings:
                    if self._is_auto_batchable(picking):
                        # Create new batch with both pickings
                        new_batch = self.env['stock.picking.batch'].sudo().create({
                            'picking_ids': [Command.link(self.id), Command.link(picking.id)],
                            'company_id': self.company_id.id if self.company_id else False,
                            'picking_type_id': self.picking_type_id.id,
                        })
                        if picking.picking_type_id.batch_auto_confirm:
                            new_batch.action_confirm()
                        return new_batch
                if self.container_id:
                    if not possible_pickings:
                        new_batch = self.env['stock.picking.batch'].sudo().create({
                            'picking_ids': [Command.link(self.id), Command.link(possible_pickings.id)],
                            'company_id': self.company_id.id if self.company_id else False,
                            'picking_type_id': self.picking_type_id.id,
                            'name': self.container_id
                        })
                        if possible_pickings.picking_type_id.batch_auto_confirm:
                            new_batch.action_confirm()
                        return new_batch

                # If nothing was found after those two steps, then no batch is doable given the conditions
                return False

        else:
            return super()._find_auto_batch()

    def action_assign(self):
        res = super().action_assign()
        for picking in self:
            picking._find_auto_batch()

        return res

    def put_in_pack_by_container_id(self):
        if not self.container_id:
            raise UserError(_('Container Id is Empty Please fill the Container ID and Proceed'))
        self._find_auto_batch()
        self.batch_id.write({'name': self.container_id})


    def _get_possible_pickings_domain(self):
        domain = super()._get_possible_pickings_domain()
        if self.picking_type_id.batch_group_by_container and self.container_id:
            domain = expression.AND([domain, [('container_id', '=', self.container_id)]])
        return domain

    def _get_possible_batches_domain(self):
        domain = super()._get_possible_batches_domain()
        if self.picking_type_id.batch_group_by_container and self.container_id:
            domain = expression.AND([domain, [('picking_ids.container_id', '=', self.container_id if self.container_id else False)]])
        return domain




