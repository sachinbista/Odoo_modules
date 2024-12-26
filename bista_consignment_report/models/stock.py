# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, Command


class StockPicking(models.Model):
    _inherit = "stock.picking"

    consignment_stock_move = fields.Boolean(string='Consignment Move', readonly=True)

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        move_line_obj = self.env['stock.move.line']
        create_bill = {}
        consignment_stock_move = self.env['ir.config_parameter'].sudo().get_param(
            'bista_consignment_report.consignment_stock_move')
        context = self._context.copy()
        for picking in self:
            for move in picking.move_ids:
                if move.restrict_partner_id:

                    move.write({
                        'move_line_ids': [
                            Command.update(move.move_line_ids.ids, {'owner_id': move.restrict_partner_id.id}),
                        ],
                        'consignment_stock_move': True if consignment_stock_move else False
                    })
                    picking.update({
                        'consignment_stock_move': True if consignment_stock_move else False,
                        'owner_id': False if consignment_stock_move else picking.owner_id.id
                    })
                for line in move.move_line_ids.filtered(lambda s: s.owner_id):
                    domain = [('product_id', '=', line.product_id.id),
                              ('owner_id', '=', line.owner_id.id),
                              ('move_id.purchase_line_id', '!=', False)]
                    if line.product_id.tracking == 'lot':
                        domain += [('lot_id', '=', line.lot_id.id)]
                    purchase_move_line_id = move_line_obj.search(domain, order='date')
                    if purchase_move_line_id and picking.picking_type_id.code not in ('internal', 'incoming'):
                        po_id = purchase_move_line_id.move_id.purchase_line_id.order_id
                        po_line = purchase_move_line_id.move_id.purchase_line_id.filtered(
                            lambda s: s.qty_invoiced != s.qty_received)
                        if po_line:
                            if po_id in create_bill:
                                create_bill[po_id] |= po_line
                            else:
                                create_bill[po_id] = po_line
            for po_id, po_line in create_bill.items():
                context.update({'purchase_line': po_line, 'move_ids': picking.move_ids})
                if po_line.qty_invoiced < po_line.qty_received:
                    po_id.with_context(context).action_create_invoice()
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    consignment_stock_move = fields.Boolean(
        string='Consignment Move',
        readonly=True)
