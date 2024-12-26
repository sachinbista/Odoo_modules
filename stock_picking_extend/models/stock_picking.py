# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models
from odoo.tests import Form

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total_case_count = fields.Integer(string="Total Case Count", compute="get_purchase_order_details")
    package_count = fields.Integer(string="Packages", compute="_total_packages_count", store=True)
    total_pallet_count = fields.Integer(string="Total Pallet Count")
    total_quantities = fields.Integer(string="Total Quantities", compute="_total_done_quantities", store="1")
    landed_cost_status = fields.Selection([('pending', 'Pending'),('done', 'Done'),('cancel', 'Not Required')],string="Landed Cost Status", default='pending')

    def button_update_landed_cost(self):
        picking_ids = self.search([('state', '=', 'cancel')])
        for picking_id in picking_ids:
            picking_id.landed_cost_status = 'cancel'

    def _action_done(self):
        for picking in self:
            if picking.owner_id:
                picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
                picking.move_line_ids.write({'owner_id': picking.owner_id.id})

            todo_moves = picking.move_ids.filtered(
                lambda move: move.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
            todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))

            purchase_order_id = picking.move_ids.mapped('purchase_line_id').mapped('order_id')
            if len(purchase_order_id) > 1:
                for purchase_order in purchase_order_id:
                    if picking.origin and picking.origin == purchase_order.name:
                        purchase_order_id = purchase_order

            if picking.picking_type_code == 'incoming' and purchase_order_id and purchase_order_id.type_of_purchase == 'dropship':
                purchase_advance_payment_inv_form = Form(self.env['purchase.advance.payment.inv']
                    .with_context(active_ids=purchase_order_id.ids, active_id=purchase_order_id.ids[0],
                    active_model='purchase.order'))
                purchase_advance_payment_inv_wiz = purchase_advance_payment_inv_form.save()
                purchase_advance_payment_inv_wiz.advance_payment_method = 'delivered'
                purchase_advance_payment_inv_wiz.create_invoices()
        return super()._action_done()

    def button_validate(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        if self.env.context.get('from_batchtransfer'):
            ctx = dict(self.env.context)
            ctx.pop('default_immediate_transfer', None)
            self = self.with_context(ctx)
    
            # Sanity checks.
            if not self.env.context.get('skip_sanity_check', False):
                self._sanity_check()
    
            self.message_subscribe([self.env.user.partner_id.id])
    
            # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
            # moves and/or the context and never call `_action_done`.
            if not self.env.context.get('button_validate_picking_ids'):
                self = self.with_context(button_validate_picking_ids=self.ids)
            res = self._pre_action_done_hook()
            if res is not True:
                return res
    
            # Call `_action_done`.
            pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
            if self.env.context.get('picking_ids_not_to_backorder'):
                pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                    lambda p: p.picking_type_id.create_backorder != 'always'
                )
            pickings_to_backorder = self - pickings_not_to_backorder
            pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
            pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
    
            if self.user_has_groups('stock.group_reception_report'):
                pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
                lines = pickings_show_report.move_ids.filtered(lambda
                                                                   m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
                if lines:
                    # don't show reception report if all already assigned/nothing to assign
                    wh_location_ids = self.env['stock.location']._search(
                        [('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids),
                         ('usage', '!=', 'supplier')])
                    if self.env['stock.move'].search([
                        ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                        ('product_qty', '>', 0),
                        ('location_id', 'in', wh_location_ids),
                        ('move_orig_ids', '=', False),
                        ('picking_id', 'not in', pickings_show_report.ids),
                        ('product_id', 'in', lines.product_id.ids)], limit=1):
                        action = pickings_show_report.action_view_reception_report()
                        action['context'] = {'default_picking_ids': pickings_show_report.ids}
                        return action
            return True
        return super().button_validate()

    @api.depends('state','move_ids_without_package.product_packaging_id')
    def get_purchase_order_details(self):
        for picking in self:
            pkg_sum = 0.0
            # if picking.origin:
            #     purchase_order = self.env['purchase.order'].search([('name', '=', picking.origin)])
            #     for line in purchase_order.mapped('order_line'):
            #         pkg_sum += line.product_packaging_qty

            if picking.state in ('waiting', 'confirmed'):
                for line in picking.move_ids_without_package:
                    if line.product_packaging_id and line.product_uom_qty > 0.0:
                        pkg_sum += line.product_uom_qty / line.product_packaging_id.qty
            if picking.state == 'assigned':
                for line in picking.move_ids_without_package:
                    if line.product_packaging_id and line.reserved_availability > 0.0:
                        pkg_sum += line.reserved_availability / line.product_packaging_id.qty
            if picking.state == 'done':
                for line in picking.move_ids_without_package:
                    if line.product_packaging_id and line.quantity_done > 0.0:
                        pkg_sum += line.quantity_done / line.product_packaging_id.qty
            picking.total_case_count = pkg_sum

    @api.depends('move_ids.quantity_done')
    def _total_done_quantities(self):
        for record in self:
            record.total_quantities = sum(move.quantity_done for move in record.move_ids)

    @api.depends('state', 'move_line_ids.result_package_id')
    def _total_packages_count(self):
        for record in self:
            packages = record.move_line_ids.mapped('result_package_id')
            record.package_count = len(packages)
            record.total_pallet_count = record.package_count

    def action_cancel(self):
        res = super().action_cancel()
        for rec in self:
            rec.landed_cost_status = 'cancel'
            if rec.batch_id.state == 'cancel':
                rec.batch_id.landed_cost_status = 'cancel'
        return res

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_confirm(self):
        rec = super(StockLandedCost, self).button_confirm()
        # Set the landed cost status to "done"
        if self.po_ids:
            for po_id in self.po_ids:
                for picking in po_id.picking_ids:
                    if picking.container_id == self.container_id:
                        picking.write({'landed_cost_status': 'done'})
                    if picking.batch_id.name == self.container_id:
                        picking.batch_id.write({'landed_cost_status': 'done'})
            
        return rec




