# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    hide_create_backorder = fields.Boolean(
        compute='_compute_hide_create_backorder')
    hide_no_backorder = fields.Boolean(
        compute='_compute_hide_no_backorder')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if res.get(
                'pick_ids') and res['pick_ids'][0] and res['pick_ids'][0][2]:
            pick_ids = self.env['stock.picking'].browse(res['pick_ids'][0][2])
            if 'hide_no_backorder' in fields and pick_ids:
                back_pick_ids = pick_ids.filtered(
                    lambda l: l.stock_transfer_id and l.picking_type_id.code == 'incoming')
                if back_pick_ids:
                    res['hide_no_backorder'] = True
            if 'hide_create_backorder' in fields and pick_ids:
                hide_pick_ids = pick_ids.filtered(
                    lambda l: l.stock_transfer_id)
                if hide_pick_ids:
                    res['hide_create_backorder'] = True
        return res

    def _compute_hide_no_backorder(self):
        for rec in self:
            rec.hide_no_backorder = False
            back_pick_ids = rec.pick_ids.filtered(
                lambda l: l.stock_transfer_id and l.picking_type_id.code == 'incoming')
            if back_pick_ids:
                rec.hide_no_backorder = True

    def _compute_hide_create_backorder(self):
        for rec in self:
            rec.hide_create_backorder = False
            hide_pick_ids = rec.pick_ids.filtered(
                lambda l: l.stock_transfer_id)
            if hide_pick_ids:
                rec.hide_create_backorder = True

    def resupply_process_cancel_backorder(self):
        self.with_context(cancel_backorder=True).process()

    def process(self):
        ctx = dict(self._context)
        if ctx.get('cancel_backorder'):
            for pick in self.pick_ids.sudo():
                if not pick.stock_transfer_id:
                    for move in pick.move_ids:
                        for origin_move in move.move_orig_ids:
                            if origin_move.state not in ['done', 'cancel']:
                                raise ValidationError((
                                    "The previous picking is still open ",
                                    "you can't process current No backorder!"))
        res = super(
            StockBackorderConfirmation,
            self).process()

        if ctx.get('cancel_backorder'):
            for pick_id in self.pick_ids:
                backorder_pick = self.env['stock.picking'].search([
                    ('backorder_id', '=', pick_id.id)])
                if backorder_pick:
                    vals = {
                        'next_picking_id': False,
                        'prev_picking_id': pick_id.id,
                        'stock_transfer_id': pick_id.stock_transfer_id.id,
                        'current_pick_warehouse': pick_id.current_pick_warehouse.id,
                    }
                    backorder_pick.write(vals)
                    backorder_pick.action_cancel()
                    pick_id.message_post(
                        body=_("Back order <em>%s</em> <b>cancelled</b>.") %
                        (",".join([b.name or '' for b in backorder_pick])))

            obj = self.env["stock.picking"]
            current_move_product = []
            for pick in self.pick_ids.sudo():
                if pick.next_picking_id:
                    for move in pick.move_ids:
                        current_move_product.append(move.product_id.id)
                        for next_move in pick.next_picking_id.move_ids:
                            if move.product_id.id == next_move.product_id.id:
                                next_move.write(
                                    {'product_uom_qty': move.quantity_done})
                    all_next_shipment = pick.stock_transfer_id.picking_ids.filtered(
                        lambda rec: rec.state not in ('cancel', 'done') and
                        rec.id > pick.id and not rec.return_picking)
                    for all_pick in all_next_shipment:
                        for next_move in all_pick.move_ids:
                            if next_move.product_id.id not in current_move_product:
                                next_move.state = 'draft'
                                next_move.unlink()
            for pic in self.pick_ids.filtered(lambda l: l.stock_transfer_id
                                              and l.stock_transfer_id.transfer_type == 'inter_company'):
                if pic.state == 'done':
                    pic_ctx = dict(self._context)
                    pic_ctx.update({'pickingid': pic.id})
                    is_in = False
                    is_out = False
                    for move_lines in pic.move_ids:
                        is_in = move_lines._is_in()
                        is_out = move_lines._is_out()

                    if is_out and not pic.return_picking:
                        invoice_id = obj.with_company(
                            pic.company_id).with_context(pic_ctx).generate_customer_invoice_backorder(
                            pic)
                        pic.invoice_id = invoice_id.id

                    if is_in and not pic.return_picking:
                        if pic.company_id != pic.sudo().prev_picking_id.company_id:
                            invoice_id = obj.with_company(
                                pic.company_id).with_context(pic_ctx).generate_vendor_invoice_backorder(
                                pic)
                            pic.invoice_id = invoice_id.id
                    elif is_in and pic.return_picking:
                        invoice_id = obj.with_company(
                            pic.company_id).with_context(pic_ctx).generate_vendor_invoice_refund_backorder(
                            pic)
                        pic.invoice_id = invoice_id.id
        return res

    def process_cancel_backorder(self):
        res = super().process_cancel_backorder()
        ctx = dict(self._context)
        if ctx.get('cancel_backorder'):
            for pick_id in self.pick_ids:
                backorder_pick = self.env['stock.picking'].search([
                    ('backorder_id', '=', pick_id.id)])
                if backorder_pick:
                    vals = {
                        'next_picking_id': False,
                        'prev_picking_id': pick_id.id,
                        'stock_transfer_id': pick_id.stock_transfer_id.id,
                        'current_pick_warehouse': pick_id.current_pick_warehouse.id,
                    }
                    backorder_pick.write(vals)
                    backorder_pick.action_cancel()
                    pick_id.message_post(
                        body=_("Back order <em>%s</em> <b>cancelled</b>.") %
                        (",".join([b.name or '' for b in backorder_pick])))
        return res
