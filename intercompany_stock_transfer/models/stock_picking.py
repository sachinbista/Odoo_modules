# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_intercompany = fields.Boolean(
        string="Resupply Operation",
        default=False,
        readonly=True)

    def read(self, fields=None, load='_classic_read'):
        ''' Added sudo to read the stock
        picking type from previous and next shipment'''
        return super(StockPickingType, self.sudo()).read(
            fields=fields, load=load)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def read(self, fields=None, load='_classic_read'):
        ''' Added sudo to read the previous and next shipment ids'''
        return super(StockPicking, self.sudo()).read(fields=fields, load=load)

    def _compute_je(self):
        for rec in self:
            rec.je_count = len(rec.mapped(
                'move_ids.account_move_ids.id'))

    def _get_loggedin_user(self):
        return self._context.get('uid')

    stock_transfer_id = fields.Many2one(
        'inter.company.stock.transfer', copy=False)
    next_picking_id = fields.Many2one('stock.picking', copy=False)
    prev_picking_id = fields.Many2one('stock.picking', copy=False)
    invoice_id = fields.Many2one("account.move", 'Invoice', copy=False)
    return_picking = fields.Boolean("Return Picking", copy=False)
    current_pick_warehouse = fields.Many2one(
        'stock.warehouse', string="Current Warehouse", copy=False)
    shipment_count = fields.Integer(
        compute="_compute_shipment",
        string='# of Transfers',
        copy=False,
        default=0)
    je_count = fields.Integer(
        compute="_compute_je",
        string='# of Entries',
        copy=False,
        default=0)
    # stock_intercompany
    is_intercompany = fields.Boolean(
        string="Resupply Operation",
        related="picking_type_id.is_intercompany")
    picking_responsible = fields.Many2one(
        'res.users', default=_get_loggedin_user, copy=False)
    intercom_sale_order_id = fields.Many2one('sale.order', 'Sale Order Ref')

    def send_to_shipper(self):
        if self.external_origin != 'go_flow':
            res = super(StockPicking, self).send_to_shipper()
            sale_id = self.sale_id or self.sale_order_id
            if sale_id:
                msg = _(
                    "Shipment sent to carrier %(carrier_name)s for shipping with "
                    "tracking number %(ref)s",
                    carrier_name=self.carrier_id.name,
                    ref=self.carrier_tracking_ref
                )
                sale_id.message_post(body=msg)
            return res

    def action_demand_autofill(self):
        for rec in self:
            rec.action_set_quantities_to_reservation()

    def action_view_journal_entries(self):
        action = self.env.ref(
            'intercompany_stock_transfer.action_move_journal_line_intercompany'
        ).read()[0]
        je_records = self.mapped('move_ids.account_move_ids.id')
        action['domain'] = [('id', 'in', je_records)]
        action['views'] = [
            (self.env.ref(
                'intercompany_stock_transfer.inter_company_journal_entry_tree'
            ).id, 'tree'),
            (self.env.ref('account.view_move_form').id, 'form'),
            (self.env.ref('account.view_account_move_kanban').id, 'kanban')]
        return action

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for pick in self.sudo():
            if pick.next_picking_id:
                for move in pick.move_ids:
                    for next_move in pick.next_picking_id.move_ids:
                        if move.product_id.id == next_move.product_id.id:
                            next_move.write(
                                {'product_uom_qty': move.quantity_done})

                if pick.next_picking_id:
                    pick.next_picking_id.with_company(
                        pick.next_picking_id.company_id
                    ).action_confirm()
                    pick.next_picking_id.with_company(
                        pick.next_picking_id.company_id
                    ).action_assign()
                # if pick.state == 'done' and \
                #         (pick.next_picking_id.picking_type_code == 'incoming'
                #          and pick.picking_type_code == 'outgoing') or \
                #         (not pick.move_ids.mapped('move_dest_ids') and
                #          not pick.move_ids.mapped('move_orig_ids') and
                #          pick.next_picking_id.picking_type_code in (
                #              'outgoing', 'internal') and
                #          pick.picking_type_code in ('incoming', 'internal')):
                #     pick.create_move_line(pick.next_picking_id)
                if pick.state == 'done' and \
                        pick.next_picking_id.picking_type_code in (
                            'internal', 'outgoing') and \
                    pick.picking_type_code in (
                            'internal', 'incoming') and \
                    pick.location_dest_id.id != pick.next_picking_id.location_id.id:
                    # if pick.next_picking_id.state not in ('draft', 'cancel',
                    # 'done'):
                    pick.out_connection_from_in(pick.next_picking_id)
                pick.next_picking_id.invoice_id = pick.invoice_id.id
            if pick.stock_transfer_id:
                if pick.stock_transfer_id.transfer_type == 'inter_company':
                    if not pick.stock_transfer_id.first_entry_date and \
                            pick.picking_type_code == 'outgoing':
                        pick.stock_transfer_id.first_entry_date = fields.Date.today()
                    elif pick.picking_type_code == 'incoming':
                        pick.stock_transfer_id.final_entry_date = fields.Date.today()
                pickings = pick.stock_transfer_id.sudo().picking_ids.filtered(
                    lambda rec: rec.state not in ['done', 'cancel'])
                if not pickings:
                    pick.stock_transfer_id.write({'state': 'done'})
        return res

    def create_move_line(self, next_picking):
        """ This function add stock move lines into
            next shipment in case if
            last shipment is not from same
            company of next shipment"""
        ctx = dict(self._context)
        for pick in self:
            if pick.company_id.id == next_picking.company_id.id:
                next_picking.move_ids._do_unreserve()
                next_picking.move_ids._compute_reserved_availability()
                next_picking.move_ids._recompute_state()

                lot_ids = {}
                for line in pick.move_line_ids.filtered(lambda l: l.lot_id):
                    if lot_ids.get(line.product_id.id):
                        lot_ids[line.product_id.id].append(line.lot_id.id)
                    else:
                        lot_ids.update({line.product_id.id: [line.lot_id.id]})

                for move_id in next_picking.move_ids:
                    m_lot_ids = lot_ids.get(move_id.product_id.id or [])
                    if m_lot_ids:
                        ctx.update({
                            'lot_numbers': m_lot_ids,
                            'is_intercompany_resupply': True})
                    move_id.with_context(ctx)._action_confirm()
            else:
                move_lines = self.env['stock.move.line']
                product_ids = []
                move_vals = []
                location_dest_id = False
                for move in next_picking.move_ids:
                    putaway_rule_ids = self.env['stock.putaway.rule'].search(
                        [('product_id', '=', move.product_id.id),
                         ('company_id', '=', move.company_id.id)])
                    if putaway_rule_ids and putaway_rule_ids[0]:
                        if move.location_dest_id.id == \
                                putaway_rule_ids[0].location_in_id.id:
                            location_dest_id = putaway_rule_ids[0].location_out_id.id
                        else:
                            location_dest_id = move.location_dest_id.id
                    else:
                        location_dest_id = move.location_dest_id.id
                    move_vals += [{
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'location_id': move.location_id.id,
                        'location_dest_id': location_dest_id,
                    }]
                    product_ids.append(move.product_id.id)
                next_picking.move_line_ids.with_context(
                    inter_company=True).unlink()
                for ml in pick.move_line_ids:
                    data = {
                        'state': 'assigned',
                        'picking_id': False,
                        'qty_done': 0.0,
                        'reserved_uom_qty': ml.qty_done,
                        'move_id': False,
                        'company_id': next_picking.company_id.id
                    }
                    new_move_line = ml.with_context(
                        tracking_disable=True).copy(
                        default=data)
                    new_move_line.with_context(tracking_disable=True).write({
                        'package_id': ml.package_id and ml.package_id.id,
                    })
                    move_lines |= new_move_line
                for vals in move_vals:
                    filter_move_lines = move_lines.filtered(
                        lambda rec: rec.product_id.id == vals.get('product_id'))
                    filter_move_lines.write({
                        'move_id': vals.get('move_id'),
                        'location_id': vals.get('location_id'),
                        'location_dest_id': vals.get('location_dest_id'),
                        'picking_id': next_picking.id,
                    })
                next_picking.action_assign()

    def out_connection_from_in(self, next_picking):
        """ This function add stock move lines into
            next shipment in case If source location of
            previous shipment does not matches to next
            shipment
        """
        for pick in self:
            move_lines = self.env['stock.move.line']
            move_vals = []
            location_dest_id = False
            for move in next_picking.move_ids:
                putaway_rule_ids = self.env['stock.putaway.rule'].search(
                    [('product_id', '=', move.product_id.id),
                     ('company_id', '=', move.company_id.id)])
                if putaway_rule_ids and putaway_rule_ids[0]:
                    if move.location_dest_id.id == putaway_rule_ids[0].location_in_id.id:
                        location_dest_id = putaway_rule_ids[0].location_out_id.id
                    else:
                        location_dest_id = move.location_dest_id.id
                else:
                    location_dest_id = move.location_dest_id.id
                move_vals += [{
                    'move': move,
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': location_dest_id,
                }]
            next_picking.move_line_ids.with_context(
                inter_company=True).unlink()
            for ml in pick.move_line_ids:
                data = {
                    'state': 'assigned',
                    'picking_id': False,
                    'qty_done': 0.0,
                    'move_id': False,
                    # 'tracking_disable':True
                }
                new_move_line = ml.with_context(
                    tracking_disable=True).copy(
                    default=data)
                new_move_line.with_context(tracking_disable=True).write({
                    'package_id': ml.package_id and ml.package_id.id,
                    # 'product_package_id': ml.product_package_id and ml.product_package_id.id
                })
                move_lines |= new_move_line

            for vals in move_vals:
                filter_move_lines = move_lines.filtered(
                    lambda rec: rec.product_id.id == vals.get('product_id'))
                filter_move_lines.write({
                    'move_id': vals.get('move_id'),
                    'location_id': vals.get('location_id'),
                    'location_dest_id': vals.get('location_dest_id'),
                    'picking_id': next_picking.id,
                })

    def create_return_move_line(self, new_picking, backorder_id):
        backorder_move_line_vals = []
        backorder_move_line_data = self.env['stock.move.line'].read_group([
            ('id', 'in', backorder_id.move_line_ids.ids)
        ], ['product_id', 'qty_done', 'lot_id', 'product_uom_id'],
            ['product_id', 'lot_id', 'product_uom_id'], lazy=False)
        backorder_lots = []
        for ml in backorder_move_line_data:
            backorder_move_line_vals.append({
                'product_id': ml['product_id'] and ml['product_id'][0],
                'quantity': ml['qty_done'],
                'lot_id': ml['lot_id'] and ml['lot_id'][0],
                'product_uom_id': ml['product_uom_id'] and ml['product_uom_id'][0],
            })
            if ml['lot_id'] and ml['lot_id'][0]:
                backorder_lots.append(ml['lot_id'][0])
        backorder_Product_ids = backorder_id.move_line_ids.mapped(
            'product_id.id')

        new_picking_vals = []
        total_lot_used = []
        for ml in backorder_id.prev_picking_id.move_line_ids:
            for back_line in backorder_move_line_vals:
                if ml.product_id.id == back_line.get('product_id') and \
                        ml.lot_id and \
                        ml.lot_id.id == back_line.get('lot_id', False):
                    remaining_qty = ml.qty_done - back_line.get('quantity')
                    if remaining_qty > 0:
                        new_picking_vals.append({
                            'product_id': ml.product_id.id,
                            # 'initial_demand': remaining_qty,
                            'qty_done': remaining_qty,
                            'lot_id': back_line.get('lot_id'),
                            'package_id': ml.package_id and ml.package_id.id,
                            # 'product_package_id': ml.product_package_id and ml.product_package_id.id,
                            'product_uom_id': back_line.get('product_uom_id'),
                            'location_id': ml.location_dest_id.id,
                            'location_dest_id': ml.location_id.id,
                            'date': fields.Datetime.now(),
                            'picking_id': new_picking.id,
                        })
                    total_lot_used.append(ml.lot_id.id)
                if ml.product_id.id == back_line.get('product_id') and \
                        ml.lot_id and \
                        ml.lot_id.id != back_line.get('lot_id', False) and \
                        ml.lot_id.id not in total_lot_used and ml.lot_id.id not in backorder_lots:
                    new_picking_vals.append({
                        'product_id': ml.product_id.id,
                        # 'initial_demand': ml.initial_demand,
                        'qty_done': ml.qty_done,
                        'lot_id': ml.lot_id.id,
                        'package_id': ml.package_id and ml.package_id.id,
                        # 'product_package_id': ml.product_package_id and ml.product_package_id.id,
                        'product_uom_id': ml.product_uom_id.id,
                        'location_id': ml.location_dest_id.id,
                        'location_dest_id': ml.location_id.id,
                        'date': fields.Datetime.now(),
                        'picking_id': new_picking.id,
                    })
                    total_lot_used.append(ml.lot_id.id)

            if ml.product_id.id not in backorder_Product_ids:
                new_picking_vals.append({
                    'product_id': ml.product_id.id,
                    # 'product_uom_qty': ml.qty_done,
                    # 'initial_demand': ml.qty_done,
                    'qty_done': ml.qty_done,
                    'lot_id': ml.lot_id.id,
                    'product_uom_id': ml.product_uom_id.id,
                    'package_id': ml.package_id and ml.package_id.id,
                    # 'product_package_id': ml.product_package_id and ml.product_package_id.id,
                    'location_id': ml.location_dest_id.id,
                    'location_dest_id': ml.location_id.id,
                    'date': fields.Datetime.now(),
                    'picking_id': new_picking.id,
                })
        new_picking.move_line_ids.with_context(inter_company=True).unlink()
        for move in new_picking.move_ids:
            for new_line in new_picking_vals:
                if new_line['product_id'] == move.product_id.id:
                    move.write({'move_line_ids': [(0, 0, new_line)]})

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        for picking in self.sudo():
            if picking.return_picking and picking.stock_transfer_id:
                raise ValidationError(_("You can not cancel return transfer."))
            elif picking.backorder_id and  \
                    picking.backorder_id.stock_transfer_id and \
                    picking.backorder_id.return_picking:
                raise ValidationError(
                    _("You can not validate return transfer partially."))

            if picking.next_picking_id:
                for move in picking.move_ids:
                    for next_move in picking.next_picking_id.move_ids:
                        if move.product_id.id == next_move.product_id.id:
                            next_move.write(
                                {'product_uom_qty': move.quantity_done})

            if picking.picking_type_code == 'outgoing' and \
                    not picking.prev_picking_id and \
                    picking.backorder_id.stock_transfer_id:
                picking.stock_transfer_id = picking.backorder_id.stock_transfer_id.id

            if picking.backorder_id and \
                    picking.backorder_id.picking_type_code == 'incoming' \
                    and picking.backorder_id.prev_picking_id \
                    and picking.backorder_id.stock_transfer_id \
                    and picking.backorder_id.prev_picking_id.state == 'done':
                picking.prev_picking_id = picking.backorder_id.prev_picking_id
                picking.stock_transfer_id = picking.backorder_id.stock_transfer_id

            if picking.picking_type_code == 'incoming' and \
                    picking.prev_picking_id and picking.stock_transfer_id and \
                    picking.prev_picking_id.state == 'done':
                if picking.backorder_id:
                    return_picking_wizard_id = self.env['stock.return.picking'].sudo().with_context(
                        action_cancel=True, no_intercompany_assign_lot=True,
                        active_id=picking.prev_picking_id.id, backorder_id=picking.id).create({})
                else:
                    return_picking_wizard_id = self.env['stock.return.picking'].sudo().with_context(
                        action_cancel=True,
                        active_id=picking.prev_picking_id.id).create({})
                action = return_picking_wizard_id.create_returns()
                if action.get('res_id', False):
                    new_picking_id = self.sudo().browse(action['res_id'])
                    new_picking_id.write({
                        # 'next_picking_id': picking.backorder_id.next_picking_id.id,
                        'next_picking_id': False,
                        'prev_picking_id': picking.backorder_id.prev_picking_id.id,
                        'invoice_id': picking.backorder_id.prev_picking_id.invoice_id.id,
                        'stock_transfer_id': picking.backorder_id.stock_transfer_id.id or False,
                        'return_picking': True,
                        'current_pick_warehouse': picking.backorder_id.\
                        prev_picking_id.current_pick_warehouse.id or False,
                    })
                    message = ('''
                    <ul class="o_mail_thread_message_tracking">
                        <li>
                            The Return of <a href=# data-oe-model='stock.picking'\
                            data-oe-id='%d'>%s</a> was generated on
                            <a href=# data-oe-model='stock.picking' data-oe-id='%d'>%s</a>
                        </li>
                    </ul>''') % (
                        picking.backorder_id.prev_picking_id.id,
                        picking.backorder_id.prev_picking_id.name,
                        new_picking_id.id, new_picking_id.name)
                    if picking and picking.backorder_id:
                        picking.backorder_id.message_post(body=message)
                        picking.backorder_id.stock_transfer_id.message_post(
                            body=message)

                    if not new_picking_id.stock_transfer_id and \
                            picking.stock_transfer_id and picking.prev_picking_id and \
                            picking.prev_picking_id.current_pick_warehouse:
                        new_picking_id.stock_transfer_id = picking.stock_transfer_id
                        new_picking_id.current_pick_warehouse = picking.prev_picking_id \
                            and picking.prev_picking_id.current_pick_warehouse
                        new_picking_id.prev_picking_id = picking.prev_picking_id
                    self.update_lot_return(
                        picking.backorder_id, new_picking_id)
                if action.get('backorder_id', False):
                    new_picking_id = self.browse(action['backorder_id'])
                    new_picking_id.write({
                        'stock_transfer_id': picking.backorder_id.stock_transfer_id.id or False,
                        'return_picking': True
                    })
            if self._context.get('all_cancel', False):
                to_cancel_picking_ids = picking.stock_transfer_id.picking_ids.filtered(
                    lambda rec: rec.state not in ('done', 'cancel') and
                    rec.return_picking == False and rec.id > picking.id)
                to_cancel_picking_ids.action_cancel()

            if picking.stock_transfer_id:
                pickings = picking.stock_transfer_id.sudo().picking_ids.filtered(
                    lambda rec: rec.state not in ['cancel'])
                done_cancel_pick = picking.stock_transfer_id.sudo().picking_ids.filtered(
                    lambda rec: rec.state not in ['done', 'cancel'])
                if not done_cancel_pick:
                    done_pick = picking.stock_transfer_id.sudo().picking_ids.filtered(
                        lambda rec: rec.state in ['done'])
                    if done_pick:
                        picking.stock_transfer_id.write({'state': 'done'})
                else:
                    picking.stock_transfer_id.write({'state': 'in_progress'})
                if not pickings:
                    picking.stock_transfer_id.write({'state': 'cancel'})
        return res

    def button_validate(self):
        res = False
        for record in self:
            if record.prev_picking_id and record.stock_transfer_id and \
                    record.stock_transfer_id.transfer_type == 'inter_company' and \
                    record.picking_type_code in ('incoming', 'outgoing'):
                for move_line in record.move_line_ids.filtered(
                        lambda line: line.lot_id):
                    prev_move_line = record.sudo().prev_picking_id.move_line_ids.filtered(
                        lambda rec: rec.product_id.id == move_line.product_id.id
                        and rec.lot_id.id == move_line.lot_id.id)
                    if prev_move_line:
                        if move_line.qty_done > sum(prev_move_line.mapped('qty_done')) or \
                            move_line.move_id.quantity_done > sum(
                                prev_move_line.mapped('move_id.quantity_done')):
                            raise ValidationError(_(
                                "You are not allow to validate more quantity for "
                                "product %s and lot %s than previous document %s" %
                                (move_line.product_id.display_name,
                                 move_line.lot_id.name, record.prev_picking_id.name)))
                    else:
                        raise ValidationError(_(
                            "You are trying to process the Product %s or lot %s "
                            "that were not specified on the previous document %s." % (
                                move_line.product_id.display_name,
                                move_line.lot_id.name, record.prev_picking_id.name)))
                if record.return_picking:
                    # over_processed_moves = self._get_overprocessed_stock_moves()
                    over_processed_moves = record.move_ids.filtered(
                        lambda move: move.product_uom_qty != 0 and
                        float_compare(move.quantity_done, move.product_uom_qty,
                                      precision_rounding=move.product_uom.rounding) == 1)
                    if over_processed_moves:
                        raise ValidationError(_(
                            "You are not allow to validate more quantity for "
                            "product %s than initial demand" % (
                                over_processed_moves[0].product_id.display_name)))

            if record.stock_transfer_id and record.stock_transfer_id.transfer_type == \
                    'inter_company' and record.prev_picking_id:
                if record.sudo().prev_picking_id.state != 'done':
                    raise ValidationError(_(
                        "Please Validate the previous transfer %s first." % (
                            record.sudo().prev_picking_id.name)))
            ctx = dict(record._context) or {}
            ctx.update({'pickingid': record.id, 'default_company_id': record.company_id.id})
            if record.stock_transfer_id and record.picking_type_id.code == 'incoming':
                ctx.update({'hide_backorder_button': True})
            res = super(StockPicking, record.with_company(
                record.company_id).with_context(ctx)).button_validate()
            if record.stock_transfer_id and \
                    record.stock_transfer_id.transfer_type == 'inter_company':
                if not record._check_backorder() and record.state == 'done':
                    is_in = False
                    is_out = False
                    for move_lines in record.move_ids:
                        is_in = move_lines._is_in()
                        is_out = move_lines._is_out()
                    if is_out and not record.return_picking:
                        if record.company_id != record.next_picking_id.sudo().company_id:
                            invoice_id = record.with_context(
                                ctx).generate_customer_invoice()
                            record.invoice_id = invoice_id.id

                    if is_in and any(record.stock_transfer_id.sudo().picking_ids.filtered(
                            lambda pick: pick.picking_type_id.code == 'outgoing' and pick.state not in ['done','cancel'])):
                        raise ValidationError(_("Please validate all the outgoing transfers first."))

                    if is_in and not record.return_picking:
                        if record.company_id != record.prev_picking_id.sudo().company_id:
                            invoice_id = record.with_context(
                                ctx).generate_vendor_invoice()
                            record.invoice_id = invoice_id.id
                    elif is_in and record.return_picking:
                        invoice_id = record.with_context(
                            ctx).generate_customer_refund_invoice()
                        record.invoice_id = invoice_id.id
                    # if is_out and self.company_id != self.next_picking_id.sudo().company_id:
                    if is_out and not any(record.stock_transfer_id.sudo().picking_ids.filtered(
                            lambda pick: pick.picking_type_id.code == 'outgoing' and pick.state not in ['done','cancel'])):
                        record.sudo().validate_intercompany_incoming()
                        record.sudo().validate_sale_picking_create_invoice()
                        record.sudo().update_origin_journal_items()

            if record.intercom_sale_order_id:
                je_ids = record.mapped('move_ids').sudo().mapped('account_move_ids')
                if je_ids:
                    sale_order_ref = record.intercom_sale_order_id.sudo().name
                    j_items = je_ids.mapped('line_ids')
                    je_ids.sudo().write({'ref': sale_order_ref})
                    j_items.sudo().write({'ref': sale_order_ref})
        return res

    def update_origin_journal_items(self):
        for record in self:
            stock_transfer_id = record.stock_transfer_id
            if stock_transfer_id:
                je_ids = self.env['account.move']
                payment_list = self.env['account.payment'].search([
                    ('stock_transfer_id', '=', stock_transfer_id.id)
                ])
                je_ids += payment_list.mapped('move_id')
                # Transfer's JE
                je_ids += stock_transfer_id.picking_ids.mapped(
                    'move_ids').mapped('account_move_ids')
                # Transfer's Invoice JE
                je_ids += stock_transfer_id.picking_ids.mapped(
                    'invoice_id')
                j_items = je_ids.mapped('line_ids')
                if j_items:
                    reference = (stock_transfer_id.sudo().sale_order_id and
                                 stock_transfer_id.sudo().sale_order_id.name or
                                 stock_transfer_id.name)
                    je_ids.sudo().write({'ref': reference})
                    j_items.sudo().write({'ref': reference})

    def validate_intercompany_incoming(self):
        self = self.sudo()
        ctx = dict(self._context)
        for rec in self:
            next_picking_id = rec.next_picking_id.sudo()
            if next_picking_id and next_picking_id.picking_type_id.code == 'incoming':
                try:
                    ctx.update({'default_company_id': next_picking_id.company_id.id})
                    next_picking_id.with_company(next_picking_id.company_id).with_context(ctx).action_assign()
                    for line in next_picking_id.move_line_ids:
                        line.qty_done = line.reserved_uom_qty
                    next_picking_id.with_company(next_picking_id.company_id).with_context(ctx).button_validate()
                except Exception as ex:
                    _logger.error(ex)
                    raise ValidationError(ex)

    def validate_sale_picking_create_invoice(self):
        self = self.sudo()
        ctx = dict(self._context)
        for rec in self:
            sale_order = rec.intercom_sale_order_id
            if sale_order:
                sale_order_company = sale_order.sudo().company_id
                sale_pickings = sale_order.picking_ids.filtered(lambda p: p.state != 'cancel')
                for pick in sale_pickings:
                    try:
                        ctx.update({'default_company_id': pick.company_id.id})
                        pick.with_company(pick.sudo().company_id).with_context(ctx).action_assign()
                        if not pick.move_line_ids:
                            for move_ids_wothout in pick.move_ids_without_package:
                                move_ids_wothout.write({'quantity_done': move_ids_wothout.product_uom_qty})
                        for line in pick.move_line_ids:
                            line.qty_done = line.reserved_uom_qty if line.reserved_uom_qty else line.move_id.product_uom_qty
                        pick.with_company(pick.sudo().company_id).with_context(ctx).button_validate()
                        move = sale_order.with_company(sale_order_company).sudo()._create_invoices()
                        move.with_company(sale_order_company).sudo().action_post()
                        move.sudo().write({'ref': sale_order.sudo().name,
                                           'external_origin': sale_order.sudo().external_origin,
                                           'goflow_store_id': sale_order.goflow_store_id and sale_order.goflow_store_id.id,
                                            })
                        move.line_ids.write({'ref': sale_order.sudo().name})
                    except Exception as ex:
                        _logger.error(ex)
                        raise ValidationError(ex)

    def _action_generate_backorder_wizard(self, show_transfers=False):
        res = super(
            StockPicking,
            self)._action_generate_backorder_wizard(
            show_transfers=show_transfers)
        if self._context.get('hide_backorder_button'):
            if res.get('name') and res.get('name') == 'Create Backorder?':
                res.update({'name': 'ATTENTION!'})
        return res

    def _create_backorder(self):
        ctx = dict(self._context)
        ctx.update({'pickingid': self.id})
        if self.env.user.has_group('base.group_user'):
            return super(StockPicking, self.with_context(ctx))._create_backorder()
        else:
            return super(StockPicking, self.with_context(ctx).sudo())._create_backorder()

    def copy(self, default=None):
        if self.env.user.has_group('base.group_user'):
            return super(StockPicking, self).copy(default=default)
        else:
            return super(StockPicking, self.sudo()).copy(default=default)

    def get_journal(self, type):
        ctx = dict(self._context)
        if ctx.get('default_journal_id', False):
            return self.env['account.journal'].browse(
                ctx.get('default_journal_id'))
        inv_type = ctx.get('move_type', type)
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = ctx.get('allowed_company_ids', [])
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty]
                            for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id and company_id[0] or False),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    def generate_customer_invoice(self):
        self = self.sudo()
        invoice_dict_line_lst = []
        obj = self.env["account.move"]
        if self.picking_type_id.code == 'outgoing':
            if self.current_pick_warehouse and\
                    not self.current_pick_warehouse.account_journal_id:
                raise ValidationError(_(
                    "Payment journal is missing at '%s' warehouse configuration")
                    % self.current_pick_warehouse.name)
            if self.sudo().next_picking_id and self.stock_transfer_id:
                if self.move_ids:
                    line_account = False
                    if self.current_pick_warehouse and \
                            self.current_pick_warehouse.account_income_id:
                        line_account = self.current_pick_warehouse.account_income_id.id
                    elif self.location_id.warehouse_id:
                        line_account = self.location_id.warehouse_id.account_income_id and \
                            self.location_id.warehouse_id.account_income_id.id or False
                    if not line_account:
                        raise ValidationError(_(
                            'Income account is missing on '
                            'warehouse configuration.'))

                    for line in self.move_ids:
                        invoice_dict_line = {
                            'product_id': line.product_id.id,
                            'quantity': line.quantity_done,
                            'product_uom_id': line.product_uom.id,
                            'name': line.product_id.name,
                            'ref': self.stock_transfer_id.name,
                            'price_unit': line.product_id.standard_price or line.product_id.lst_price,
                            'display_type': 'product',
                            'account_id': line_account,
                            'company_id': self.company_id.id
                        }
                        invoice_dict_line_lst.append((0, 0, invoice_dict_line))
                    journal_id = self.with_company(
                        self.company_id).get_journal('out_invoice')

                    if not journal_id:
                        raise ValidationError(_(
                            'Invoice Journal is missing on configuration.'))

                    pre_partner = self.sudo().next_picking_id.company_id.partner_id
                    invoice_dict = {
                        'move_type': 'out_invoice',
                        'invoice_origin': self.stock_transfer_id.name,
                        'partner_id': pre_partner and pre_partner.id,
                        'journal_id': journal_id.id,
                        'stock_transfer_id': self.stock_transfer_id.id or False,
                        'ref': self.stock_transfer_id.name,
                        'user_id': self.env.user.id,
                        'resupply_picking_id': self.id,
                        'invoice_line_ids': invoice_dict_line_lst,
                        'company_id': self.company_id.id
                    }
                    if self.env.user.has_group('base.group_user'):
                        invoice_id = obj.with_company(
                            self.company_id).create(invoice_dict)
                    else:
                        obj = obj.sudo()
                        invoice_id = obj.with_company(
                            self.company_id).create(invoice_dict)
                    if invoice_id and invoice_id.invoice_line_ids:
                        invoice_id.with_company(
                            self.company_id).with_context(
                            resupply_transfer_id=self.stock_transfer_id.name).action_post()

                        if invoice_id.state == 'posted' and\
                                invoice_id.payment_state == 'not_paid':
                            # Start Payment Register create code
                            partner_type = False
                            payment_type = False

                            if self.picking_type_id.code == 'incoming':
                                if self.return_picking:
                                    payment_type = 'inbound'
                                else:
                                    payment_type = 'outbound'
                                partner_type = 'supplier'

                            if self.picking_type_id.code == 'outgoing':
                                if self.return_picking:
                                    payment_type = 'outbound'
                                else:
                                    payment_type = 'inbound'
                                partner_type = 'customer'

                            journal_id = False
                            if self.current_pick_warehouse:
                                journal_id = self.current_pick_warehouse.account_journal_id
                            elif self.picking_type_id.warehouse_id:
                                warehouse_id = self.picking_type_id.warehouse_id
                                journal_id = warehouse_id and\
                                    warehouse_id.account_journal_id or False

                            if not self.current_pick_warehouse:
                                raise ValidationError(_(
                                    'Warehouse is missing on current shipment.'))
                            if not journal_id:
                                raise ValidationError(_(
                                    'Payment Journal is missing on'
                                    ' Warehouse configuration.'))

                            res_id = self.env['account.payment.register'].sudo().with_company(
                            self.company_id).with_context(
                                resupply_transfer_id=self.stock_transfer_id.name,
                                active_ids=invoice_id.ids,
                                active_model='account.move',
                                default_journal_id=journal_id.id,
                                default_payment_type=payment_type,
                                default_partner_type=partner_type,
                                default_company_id=self.company_id.id).create({})
                            payments = res_id.sudo().with_company(self.company_id)._create_payments()
                            if payments:
                                payments.sudo().write({
                                    'stock_transfer_id': self.stock_transfer_id.id
                                })
                            # End PRC
                    return invoice_id

    def generate_customer_invoice_backorder(self, picking_id):
        self = self.sudo()
        invoice_dict_line_lst = []
        obj = self.env["account.move"]
        if picking_id and picking_id.picking_type_id.code == 'outgoing':
            if picking_id.sudo().next_picking_id and \
                    picking_id.stock_transfer_id:
                if picking_id and picking_id.move_ids:

                    line_account = False
                    if picking_id.with_company(
                            picking_id.company_id).current_pick_warehouse and \
                            picking_id.with_company(picking_id.company_id).\
                            current_pick_warehouse.account_income_id:
                        line_account = picking_id.with_company(picking_id.company_id)\
                            .current_pick_warehouse.account_income_id.id or False
                    elif picking_id.with_company(picking_id.company_id).location_id.warehouse_id\
                            and picking_id.with_company(picking_id.company_id)\
                            .location_id.warehouse_id.account_income_id:
                        line_account = picking_id.with_company(
                            picking_id.company_id).location_id\
                            .warehouse_id.account_income_id.id or False
                    if not line_account:
                        raise ValidationError(_(
                            'Income account is missing on '
                            'warehouse configuration.'))

                    for line in picking_id.move_ids:
                        invoice_dict_line = {
                            'product_id': line.product_id.id,
                            'quantity': line.quantity_done,
                            'product_uom_id': line.product_uom.id,
                            'name': line.product_id.name,
                            'ref': picking_id.stock_transfer_id.name,
                            'price_unit': line.product_id.standard_price or line.product_id.lst_price,
                            'account_id': line_account,
                            'display_type': 'product',
                            'company_id': self.company_id.id
                        }
                        invoice_dict_line_lst.append(invoice_dict_line)
                    journal_id = self.with_company(
                        picking_id.company_id).get_journal('out_invoice')
                    if not journal_id:
                        raise ValidationError(_(
                            'Journal is missing on configuration.'))
                    invoice_dict = {
                        'move_type': 'out_invoice',
                        'invoice_origin': picking_id.stock_transfer_id.name,
                        'partner_id': picking_id.partner_id and picking_id.partner_id.id,
                        'journal_id': journal_id.id,
                        'invoice_line_ids': [(0, 0, l) for l in invoice_dict_line_lst],
                        'stock_transfer_id': picking_id.stock_transfer_id.id,
                        'ref': picking_id.stock_transfer_id.name,
                        'user_id': self.env.user.id,
                        'resupply_picking_id': picking_id.id,
                        'company_id': self.company_id.id
                    }
                    if self.env.user.has_group('base.group_user'):
                        invoice_id = obj.with_company(
                            picking_id.company_id).create(invoice_dict)
                    else:
                        invoice_id = obj.sudo().with_company(
                            picking_id.company_id).create(invoice_dict)

                    if invoice_id and invoice_id.invoice_line_ids:
                        invoice_id.sudo().with_company(
                            picking_id.company_id).with_context(
                            resupply_transfer_id=picking_id.stock_transfer_id.name).action_post()
                        if invoice_id.state == 'posted' and\
                                invoice_id.payment_state == 'not_paid':
                            # Start Payment Register create code
                            journal_id = False
                            if self.current_pick_warehouse:
                                journal_id = self.current_pick_warehouse.account_journal_id
                            elif self.picking_type_id.warehouse_id:
                                warehouse_id = self.picking_type_id.warehouse_id
                                journal_id = warehouse_id and\
                                    warehouse_id.account_journal_id or False

                            if not self.current_pick_warehouse:
                                raise ValidationError(_(
                                    'Warehouse is missing on current shipment.'))
                            if not journal_id:
                                raise ValidationError(_(
                                    'Payment Journal is missing on'
                                    ' Warehouse configuration.'))

                            res_id = self.env['account.payment.register'].sudo().with_company(
                                self.company_id).with_context(
                                resupply_transfer_id=picking_id.stock_transfer_id.name,
                                active_ids=invoice_id.ids,
                                active_model='account.move',
                                default_journal_id=journal_id.id,
                                default_payment_type='inbound',
                                default_partner_type='customer',
                                default_company_id=self.company_id.id).create({})
                            payments = res_id.sudo().with_company(self.company_id)._create_payments()
                            if payments:
                                payments.sudo().write(
                                    {'stock_transfer_id': self.stock_transfer_id.id})
                            # End PRC
                    return invoice_id

    def generate_vendor_invoice_backorder(self, picking_id):
        self = self.sudo()
        invoice_dict_line_lst = []
        obj = self.env["account.move"]
        if picking_id.picking_type_id.code == 'incoming':
            if picking_id.sudo().prev_picking_id and \
                    picking_id.stock_transfer_id:
                if picking_id.move_ids:

                    for line in picking_id.move_ids:
                        line_account = False
                        if line.product_id.with_company(picking_id.company_id)\
                                .categ_id.property_stock_account_input_categ_id:
                            line_account = line.product_id.with_company(
                                picking_id.company_id).categ_id.property_stock_account_input_categ_id.id
                        # elif line.product_id.with_company(picking_id.company_id)\
                        #         .property_stock_account_input:
                        #     line_account = line.product_id.with_company(
                        #         picking_id.company_id).property_stock_account_input.id
                        if not line_account:
                            raise ValidationError(_(
                                'Expense account is missing'
                                'on warehouse configuration.'))

                        invoice_dict_line = {
                            'product_id': line.product_id.id,
                            'quantity': line.quantity_done,
                            'product_uom_id': line.product_uom.id,
                            'name': line.product_id.name,
                            'ref': picking_id.stock_transfer_id.name,
                            'price_unit': line.product_id.standard_price or line.product_id.lst_price,
                            'account_id': line_account,
                            'display_type': 'product',
                            'company_id': self.company_id.id
                        }
                        invoice_dict_line_lst.append(invoice_dict_line)

                    journal_id = self.with_company(
                        picking_id.company_id).get_journal('in_invoice')
                    if not journal_id:
                        raise ValidationError(_(
                            'Journal is missing on configuration.'))

                    pre_partner = picking_id.sudo().prev_picking_id.company_id.partner_id
                    invoice_dict = {
                        'move_type': 'in_invoice',
                        'invoice_date': fields.Date.today(),
                        'invoice_origin': picking_id.stock_transfer_id.name,
                        'partner_id': pre_partner and pre_partner.id,
                        'journal_id': journal_id.id,
                        'invoice_line_ids': [(0, 0, l) for l in invoice_dict_line_lst],
                        'stock_transfer_id': picking_id.stock_transfer_id.id or False,
                        'ref': picking_id.stock_transfer_id.name,
                        'user_id': self.env.user.id,
                        'resupply_picking_id': picking_id.id,
                        'company_id': self.company_id.id
                    }
                    if self.env.user.has_group('base.group_user'):
                        invoice_id = obj.with_company(
                            picking_id.company_id).create(invoice_dict)
                    else:
                        invoice_id = obj.sudo().with_company(
                            picking_id.company_id).create(invoice_dict)

                    if invoice_id and invoice_id.invoice_line_ids:
                        invoice_id.sudo().with_company(
                            picking_id.company_id).with_context(
                            resupply_transfer_id=picking_id.stock_transfer_id.name).action_post()
                        if invoice_id.state == 'posted' and\
                                invoice_id.payment_state == 'not_paid':
                            # Start Payment Register create code
                            journal_id = False
                            warehouse_id = False
                            if picking_id.current_pick_warehouse:
                                warehouse_id = picking_id.current_pick_warehouse
                                journal_id = picking_id.current_pick_warehouse.account_journal_id
                            elif picking_id.picking_type_id.warehouse_id:
                                warehouse_id = picking_id.picking_type_id.warehouse_id
                                journal_id = warehouse_id and warehouse_id.account_journal_id or False

                            if not warehouse_id:
                                raise ValidationError(_(
                                    'Warehouse is missing on current shipment.'))
                            if not journal_id:
                                raise ValidationError(_(
                                    'Payment Journal is missing on'
                                    ' Warehouse configuration.'))

                            res_id = self.env['account.payment.register'].sudo().with_company(
                                self.company_id).with_context(
                                resupply_transfer_id=picking_id.stock_transfer_id.name,
                                active_ids=invoice_id.ids,
                                active_model='account.move',
                                default_journal_id=journal_id.id,
                                default_payment_type='outbound',
                                default_partner_type='supplier',
                                default_company_id=self.company_id.id).create({})
                            payments = res_id.sudo().with_company(self.company_id)._create_payments()
                            if payments:
                                payments.sudo().write(
                                    {'stock_transfer_id': self.stock_transfer_id.id})
                            # End PRC
                    return invoice_id

    def generate_vendor_invoice(self):
        invoice_dict_line_lst = []
        company_id = self.company_id
        self = self.sudo()
        obj = self.env["account.move"]
        pre_partner = self.sudo().prev_picking_id.company_id.partner_id
        if self.picking_type_id.code == 'incoming':
            if self.sudo().prev_picking_id and self.stock_transfer_id:
                if self.move_ids:
                    for line in self.move_ids:
                        line_account = False
                        line = line.with_company(company_id)
                        product_id = line.product_id
                        if product_id.with_company(company_id)\
                                .categ_id.property_stock_account_input_categ_id:
                            line_account = product_id.with_company(
                                company_id).categ_id.property_stock_account_input_categ_id
                        # elif line.product_id.with_company(self.company_id)\
                        #         .property_stock_account_input:
                        #     line_account = line.product_id.with_company(
                        #         self.company_id).property_stock_account_input
                        if not line_account:
                            raise ValidationError(_(
                                'Expense account is missing'
                                'on warehouse configuration.'))
                        invoice_dict_line = {
                            'product_id': product_id.id,
                            'quantity': line.quantity_done,
                            'product_uom_id': line.product_uom.id,
                            'name': product_id.name,
                            'ref': self.stock_transfer_id.name,
                            'price_unit': product_id.standard_price or product_id.lst_price,
                            'account_id': line_account and line_account.id or False,
                            'display_type': 'product',
                            'company_id': company_id.id
                        }
                        invoice_dict_line_lst.append(invoice_dict_line)
                    journal_id = self.with_company(
                        company_id).get_journal('in_invoice')
                    if not journal_id:
                        raise ValidationError(_(
                            'Journal is missing on configuration.'))

                    invoice_dict = {
                        'invoice_date': fields.Date.today(),
                        'move_type': 'in_invoice',
                        'invoice_origin': self.stock_transfer_id.name,
                        'partner_id': pre_partner.id,
                        'invoice_line_ids': [(0, 0, l) for l in invoice_dict_line_lst],
                        'stock_transfer_id': self.stock_transfer_id.id or False,
                        'ref': self.stock_transfer_id.name,
                        'resupply_picking_id': self.id,
                        'journal_id': journal_id.id,
                        'company_id': company_id.id
                    }
                    invoice_id = obj.sudo().with_company(company_id).create(invoice_dict)
                    if invoice_id and invoice_id.invoice_line_ids:
                        invoice_id.sudo().with_company(
                            company_id).with_context(
                            resupply_transfer_id=self.stock_transfer_id.name).action_post()
                        if invoice_id.state == 'posted' and\
                                invoice_id.payment_state == 'not_paid':
                            # Start Payment Register create code
                            journal_id = False
                            if self.current_pick_warehouse:
                                journal_id = self.current_pick_warehouse.account_journal_id
                            elif self.picking_type_id.warehouse_id:
                                warehouse_id = self.picking_type_id.warehouse_id
                                journal_id = warehouse_id and\
                                    warehouse_id.account_journal_id or False

                            if not self.current_pick_warehouse:
                                raise ValidationError(_(
                                    'Warehouse is missing on current shipment.'))
                            if not journal_id:
                                raise ValidationError(_(
                                    'Payment Journal is missing on'
                                    ' Warehouse configuration.'))
                            res_id = self.env[
                                'account.payment.register'].with_company(
                                company_id).with_context(
                                active_ids=invoice_id.ids,
                                active_model='account.move',
                                default_journal_id=journal_id.id,
                                default_payment_type='outbound',
                                default_partner_type='supplier',
                                default_company_id=company_id.id
                            ).sudo().create({})
                            payments = res_id.with_company(company_id).sudo()._create_payments()
                            if payments:
                                payments.sudo().write(
                                    {'stock_transfer_id': self.stock_transfer_id.id})
                            # End PRC
                    return invoice_id

    def generate_customer_refund_invoice(self):
        invoice_dict_line_lst = []
        obj = self.env["account.move"]
        if self.sudo().prev_picking_id and self.stock_transfer_id:
            if self.move_ids:
                line_account = False
                if self.current_pick_warehouse and \
                    self.current_pick_warehouse.with_company(
                        self.company_id).account_income_id:
                    line_account = self.current_pick_warehouse.with_company(
                        self.company_id).account_income_id
                elif self.location_dest_id.warehouse_id and \
                    self.location_dest_id.with_company(
                        self.company_id).warehouse_id.account_income_id:
                    line_account = self.location_dest_id.with_company(
                        self.company_id).warehouse_id.account_income_id or False
                if not line_account:
                    raise ValidationError(_(
                        'Income account is missing on '
                        'warehouse configuration.'))
                for line in self.move_ids:
                    invoice_dict_line = {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity_done,
                        'product_uom_id': line.product_uom.id,
                        'name': line.product_id.name,
                        'ref': self.stock_transfer_id.name,
                        'price_unit': line.product_id.standard_price or line.product_id.lst_price,
                        'account_id': line_account.id,
                        'display_type': 'product',
                    }
                    invoice_dict_line_lst.append(invoice_dict_line)
                journal_id = self.with_company(
                    self.company_id).get_journal('out_refund')
                if not journal_id:
                    raise ValidationError(_(
                        'Journal is missing on configuration.'))
                invoice_dict = {
                    'move_type': 'out_refund',
                    'reversed_entry_id': self.invoice_id.id,
                    'invoice_origin': self.stock_transfer_id.name,
                    'partner_id': self.partner_id and self.partner_id.id,
                    'journal_id': journal_id.id,
                    'invoice_line_ids': [(0, 0, l) for l in invoice_dict_line_lst],
                    'stock_transfer_id': self.stock_transfer_id.id,
                    'user_id': self.env.user.id,
                    'resupply_picking_id': self.id
                }
                if self.env.user.has_group('base.group_user'):
                    invoice_id = obj.with_company(
                        self.company_id).create(invoice_dict)
                else:
                    invoice_id = obj.sudo().with_company(
                        self.company_id).create(invoice_dict)

                if invoice_id and invoice_id.invoice_line_ids:
                    invoice_id.with_context(
                        resupply_transfer_id=self.stock_transfer_id.name).action_post()

                    if invoice_id.state == 'posted' and\
                            invoice_id.payment_state == 'not_paid':
                        # Start Payment Register create code

                        journal_id = False
                        if self.current_pick_warehouse:
                            journal_id = self.current_pick_warehouse.account_journal_id
                        elif self.picking_type_id.warehouse_id:
                            warehouse_id = self.picking_type_id.warehouse_id
                            journal_id = warehouse_id and\
                                warehouse_id.account_journal_id or False

                        if not self.current_pick_warehouse:
                            raise ValidationError(_(
                                'Warehouse is missing on current shipment.'))
                        if not journal_id:
                            raise ValidationError(_(
                                'Payment Journal is missing on'
                                ' Warehouse configuration.'))

                        res_id = self.env['account.payment.register']\
                            .with_context(
                                resupply_transfer_id=self.stock_transfer_id.name,
                                active_ids=invoice_id.ids,
                                active_model='account.move',
                                default_journal_id=journal_id.id,
                                default_payment_type='outbound',
                                default_partner_type='customer',)\
                            .create({})
                        payments = res_id._create_payments()
                        if payments:
                            payments.sudo().write(
                                {'stock_transfer_id': self.stock_transfer_id.id})
                        # End PRC
                return invoice_id

    def generate_vendor_invoice_refund_backorder(self, picking_id):
        invoice_dict_line_lst = []
        obj = self.env["account.move"]
        if picking_id.picking_type_id.code in ('incoming', 'outgoing'):
            if picking_id.sudo().prev_picking_id and \
                    picking_id.stock_transfer_id:
                if picking_id.move_ids:
                    line_account = False
                    if picking_id.with_company(
                            picking_id.company_id).current_pick_warehouse and \
                            picking_id.with_company(
                            picking_id.company_id).current_pick_warehouse.account_income_id:
                        line_account = picking_id.with_company(
                            picking_id.company_id).current_pick_warehouse.account_income_id.id
                    elif picking_id.with_company(
                            picking_id.company_id).location_dest_id.warehouse_id and\
                            picking_id.with_company(
                            picking_id.company_id).location_dest_id.warehouse_id.account_income_id:
                        line_account = picking_id.with_company(
                            picking_id.company_id).location_dest_id.\
                            warehouse_id.account_income_id.id or False

                    if not line_account:
                        raise ValidationError(_(
                            'Income account is missing on '
                            'warehouse configuration.'))

                    for line in picking_id.move_ids:
                        invoice_dict_line = {
                            'product_id': line.product_id.id,
                            'quantity': line.quantity_done,
                            'product_uom_id': line.product_uom.id,
                            'name': line.product_id.name,
                            'ref': picking_id.stock_transfer_id.name,
                            'price_unit': line.product_id.standard_price or line.product_id.lst_price,
                            'account_id': line_account,
                            'display_type': 'product',
                        }
                        invoice_dict_line_lst.append(invoice_dict_line)

                    journal_id = self.with_company(
                        picking_id.company_id).get_journal('out_invoice')
                    if not journal_id:
                        raise ValidationError(_(
                            'Journal is missing on configuration.'))
                    invoice_dict = {
                        'move_type': 'out_refund',
                        'reversed_entry_id': picking_id.invoice_id.id,
                        'invoice_origin': picking_id.stock_transfer_id.name,
                        'partner_id': picking_id.partner_id and picking_id.partner_id.id,
                        'journal_id': journal_id.id,
                        'invoice_line_ids': [(0, 0, l) for l in invoice_dict_line_lst],
                        'stock_transfer_id': picking_id.stock_transfer_id.id,
                        'user_id': picking_id.env.user.id,
                        'resupply_picking_id': picking_id.id,
                    }
                    if self.env.user.has_group('base.group_user'):
                        invoice_id = obj.with_company(
                            picking_id.company_id).create(invoice_dict)
                    else:
                        invoice_id = obj.sudo().with_company(
                            picking_id.company_id).create(invoice_dict)
                    # invoice_id = invoice_id.with_company(
                        # picking_id.company_id.id)
                    if invoice_id and invoice_id.invoice_line_ids:
                        invoice_id.with_context(
                            resupply_transfer_id=picking_id.stock_transfer_id.name).action_post()

                        if invoice_id.state == 'posted' and\
                                invoice_id.payment_state == 'not_paid':
                            # Start Payment Register create code

                            journal_id = False
                            warehouse_id = False
                            if picking_id.current_pick_warehouse:
                                warehouse_id = picking_id.current_pick_warehouse
                                journal_id = picking_id.current_pick_warehouse.account_journal_id
                            elif picking_id.picking_type_id.warehouse_id:
                                warehouse_id = picking_id.picking_type_id.warehouse_id
                                journal_id = warehouse_id and warehouse_id.account_journal_id or False

                            if not warehouse_id:
                                raise ValidationError(_(
                                    'Warehouse is missing on current shipment.'))
                            if not journal_id:
                                raise ValidationError(_(
                                    'Payment Journal is missing on'
                                    ' Warehouse configuration.'))

                            res_id = self.env['account.payment.register']\
                                .with_context(
                                    resupply_transfer_id=picking_id.stock_transfer_id.name,
                                    active_ids=invoice_id.ids,
                                    active_model='account.move',
                                    default_journal_id=journal_id.id,
                                    default_payment_type='outbound',
                                    default_partner_type='supplier',)\
                                .create({})
                            payments = res_id._create_payments()
                            if payments:
                                payments.sudo().write(
                                    {'stock_transfer_id': picking_id.stock_transfer_id.id})
                            # End PRC
                    return invoice_id

    def update_lot_return(self, picking_id, return_picking):
        if picking_id.move_line_ids and return_picking.move_line_ids:
            for current_line in picking_id.move_line_ids:
                for next_line in return_picking.backorder_id.move_line_ids:
                    if current_line.product_id.id == next_line.product_id.id \
                            and current_line.product_id:
                        next_line.lot_id = current_line.lot_id.id
                        next_line.lot_name = current_line.lot_id.name

    @api.depends('next_picking_id')
    def _compute_shipment(self):
        for rec in self:
            if rec.sudo().next_picking_id and \
                    self.env.user.company_id == rec.sudo().next_picking_id.company_id:
                rec.shipment_count = len(rec.sudo().next_picking_id) or 0
            else:
                rec.shipment_count = 0

    def action_view_Picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(self.next_picking_id) > 1:
            action['views'] = [
                (self.env.ref(
                    'intercompany_stock_transfer.inter_company_picktree').id, 'tree'),
                (self.env.ref('stock.view_picking_form').id, 'form'),
                (self.env.ref('stock.stock_picking_kanban').id, 'kanban')]
        else:
            action['views'] = [
                (self.env.ref('stock.view_picking_form').id, 'form')]
        for rec in self:
            if self.env.user.company_id == rec.sudo().next_picking_id.company_id:
                action['res_id'] = self.sudo().next_picking_id.id
        return action
