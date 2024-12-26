# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

import string


class InterCompanyStockTransfer(models.Model):
    _name = 'inter.company.stock.transfer'
    _description = 'Resupply Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    READONLY_STATES = {
        'in_progress': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char(
        string='Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'))
    origin = fields.Char(string='Source Document', copy=False)
    user_id = fields.Many2one(
        'res.users', default=lambda self: self.env.user,
        string='Created By')
    transfer_type = fields.Selection([
        ('inter_warehouse', 'Inter Warehouse'),
        ('inter_company', 'Inter Company'),
        ('internal_resupply', 'Internal Resupply')
    ], default='inter_warehouse',
        string='Transfer Type',
        states=READONLY_STATES)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True,
        copy=False, index=True, default='draft')
    scheduled_date = fields.Datetime(
        required=True, index=True,
        string='Expected Delivery Date', copy=False,
        default=lambda self: fields.Datetime.now(),
        states=READONLY_STATES)
    exp_arrival_date = fields.Datetime(
        index=True,
        string='Expected Arrival Date', copy=False,
        states=READONLY_STATES)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.user.company_id,
        states=READONLY_STATES)
    dest_company_id = fields.Many2one(
        'res.company',
        string='Destination Company',
        states=READONLY_STATES)
    warehouse_id = fields.Many2one(
        'stock.warehouse', required=True,
        states=READONLY_STATES)
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        states=READONLY_STATES)
    final_dest_location_id = fields.Many2one(
        'stock.location',
        string="Destination Location",
        copy=False)
    line_ids = fields.One2many(
        'inter.company.stock.transfer.line',
        'stock_transfer_id',
        states=READONLY_STATES, copy=True)
    crossdock_route_ids = fields.One2many(
        'cross.dock.route.line',
        'stock_transfer_id', copy=True,
        states=READONLY_STATES)
    picking_ids = fields.One2many(
        'stock.picking', 'stock_transfer_id')
    transfer_count = fields.Integer(
        compute="_compute_transfer",
        string='# of Transfers',
        copy=False, default=0)
    group_id = fields.Many2one(
        'procurement.group', copy=False)
    created_from_inv_report = fields.Boolean(
        copy=False)
    je_count = fields.Integer(
        compute="_compute_je",
        string='# of Entries', copy=False,
        default=0)
    accounting_state = fields.Selection([
        ('unbalanced', 'Unbalanced'),
        ('balanced', 'Balanced')
    ], string='Journal Entry Status',
        compute='_get_accounting_status',
        copy=False, default='balanced',
        compute_sudo=True, store=True)
    first_entry_date = fields.Date(
        'First Entry Date', copy=False)
    final_entry_date = fields.Date(
        'Final Entry Date', copy=False)
    parent_location_id = fields.Many2one(
        'stock.location', 'Parent Location')
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    is_single_ship = fields.Boolean(
        string="Single Ship", compute='compute_is_single_ship', store=True)
    goflow_store_id = fields.Many2one(
        related="sale_order_id.goflow_store_id",
        string='Goflow Store', store=True)

    @api.depends('line_ids', 'line_ids.is_single_ship')
    def compute_is_single_ship(self):
        for rec in self:
            is_single_ship = False
            if any(rec.line_ids.filtered(lambda l: l.is_single_ship)):
                is_single_ship = True
            rec.is_single_ship = is_single_ship

    def _creation_message(self):
        if self.sale_order_id:
            sale_order_ref = """<a href=# data-oe-model=sale.order 
            data-oe-id=%s>%s</a>""" % (self.sale_order_id.id, self.sale_order_id.name)
            return _("Resupply Transfer created for sale order: %s" % sale_order_ref)
        return super()._creation_message()

    @api.constrains('line_ids',
                    'warehouse_id',
                    'dest_warehouse_id',
                    'transfer_type')
    def check_lot_quantity(self):
        self = self.sudo()
        source_warehouse = self.warehouse_id and self.warehouse_id.id or False
        dest_warehouse = self.dest_warehouse_id and self.dest_warehouse_id.id or False
        if self.transfer_type in ('inter_company', 'inter_warehouse'):
            if source_warehouse and dest_warehouse and source_warehouse != dest_warehouse:
                msg = ''
                lot_ids = []
                lot_loc_ids = []
                for line in self.line_ids:
                    if line.product_id and line.location_id and \
                            line.lot_id:
                        wh_qty_available = line.product_id.with_context(
                            lot_id=line.lot_id.id,
                            warehouse=source_warehouse).qty_available
                        # loc_qty_available = line.product_id.with_context(
                        #     lot_id=line.lot_id.id,
                        #     location=line.location_id.id).qty_available
                        loc_quant = self.env['stock.quant'].search([
                            ('product_id', '=', line.product_id.id),
                            ('location_id', '=', line.location_id.id),
                            ('lot_id', '=', line.lot_id.id)])
                        loc_quant_available = loc_quant.available_quantity
                        line_lot_qty = sum(self.line_ids.filtered(
                            lambda l: l.lot_id.id == line.lot_id.id).mapped(
                            'product_uom_qty'))
                        line_lot_loc_qty = sum(self.line_ids.filtered(
                            lambda l: l.lot_id.id == line.lot_id.id and
                            l.location_id.id == line.location_id.id).mapped(
                            'product_uom_qty'))
                        if line_lot_qty != wh_qty_available and line.lot_id.id not in lot_ids:
                            lot_ids.append(line.lot_id.id)
                            quants = self.env['stock.quant'].search([
                                ('product_id', '=', line.product_id.id),
                                ('warehouse_id', '=', self.warehouse_id.id),
                                ('lot_id', '=', line.lot_id.id)])
                            for quant in quants:
                                msg += F"Lot: {quant.lot_id.name}, " \
                                    F"Location: {quant.location_id.display_name}, " \
                                    F"Available Quantity: {quant.available_quantity}\n"
                        elif line_lot_qty == wh_qty_available and \
                                line_lot_loc_qty != loc_quant_available and \
                                line.lot_id.id not in lot_loc_ids:
                            lot_loc_ids.append(line.lot_id.id)
                            msg += F"Lot: {line.lot_id.name}, " \
                                F"Location: {line.location_id.display_name}, " \
                                F"Available Quantity: {loc_quant_available}\n"
                if msg:
                    msg = "You can not transfer more or less than available " \
                          "quantity of lot/ package between two different " \
                          "warehouses.\n" + msg
                    raise ValidationError(_(msg))

    @api.constrains('line_ids')
    def check_line_location_id(self):
        parent_location_ids = []
        for line in self.line_ids:
            if line.location_id.location_id.usage == 'internal':
                parent_location_id = line.location_id.location_id
            else:
                parent_location_id = line.location_id
            while parent_location_id.location_id.usage == 'internal':
                parent_location_id = parent_location_id.location_id
            parent_location_ids.append(parent_location_id.id)
        parent_location_ids = set(parent_location_ids)
        if parent_location_ids and len(set(parent_location_ids)) > 1:
            raise UserError(
                _('You can not create transfer from multiple parent locations.'))
        elif parent_location_ids:
            self.parent_location_id = list(parent_location_ids)[0]

    @api.depends('picking_ids.invoice_id')
    def _get_accounting_status(self):
        self = self.sudo()
        for rec in self:
            accounting_state = 'unbalanced'
            if rec.transfer_type == 'inter_company' and rec.first_entry_date:
                in_out_picking_ids = rec.picking_ids.filtered(
                    lambda pick: pick.picking_type_code in (
                        'incoming', 'outgoing')
                    and pick.state == 'done')
                if in_out_picking_ids.filtered(
                        lambda pick: not pick.invoice_id):
                    accounting_state = 'unbalanced'
                else:
                    balance_out = False
                    balance_in = False
                    je_payment_credit_amount = 0.0
                    je_credit_amount = 0.0
                    je_debit_amount = 0.0
                    je_payment_debit_amount = 0.0
                    for picking in in_out_picking_ids.filtered(
                        lambda pick: pick.picking_type_code == 'outgoing'
                            and pick.invoice_id):
                        je_line_ids = picking.invoice_id.line_ids
                        je_credit_line_ids = je_line_ids.filtered(
                            lambda line: line.account_id.account_type == 'asset_receivable')
                        je_credit_amount += round(sum(
                            je_credit_line_ids.mapped('debit')), 2)
                        # This code for find to payments
                        je_pay_term_lines = picking.invoice_id.line_ids \
                            .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
                        je_payment_ar_line_ids = self.env['account.move.line']
                        for partial in je_pay_term_lines.mapped(
                                'matched_debit_ids'):
                            je_payment_ar_line_ids += partial.debit_move_id
                        for partial in je_pay_term_lines.mapped(
                                'matched_credit_ids'):
                            je_payment_ar_line_ids += partial.credit_move_id

                        je_payment_credit_amount += round(sum(
                            je_payment_ar_line_ids.mapped('credit')), 2)
                        if abs(je_credit_amount - je_payment_credit_amount) <= 0.5:
                            balance_out = True
                    for picking in in_out_picking_ids.filtered(
                        lambda pick: pick.picking_type_code == 'incoming'
                            and pick.invoice_id):
                        je_line_ids = picking.invoice_id.line_ids
                        je_debit_line_ids = je_line_ids.filtered(
                            lambda line: line.account_id.account_type == 'liability_payable')
                        je_debit_amount += round(sum(
                            je_debit_line_ids.mapped('credit')), 2)
                        # This code for find to payments
                        je_debit_pay_term_lines = picking.invoice_id.line_ids \
                            .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
                        je_debit_payment_ar_line_ids = self.env['account.move.line']
                        for partial in je_debit_pay_term_lines.mapped(
                                'matched_debit_ids'):
                            je_debit_payment_ar_line_ids += partial.debit_move_id
                        for partial in je_debit_pay_term_lines.mapped(
                                'matched_credit_ids'):
                            je_debit_payment_ar_line_ids += partial.credit_move_id

                        je_payment_debit_amount += round(sum(
                            je_debit_payment_ar_line_ids.mapped('debit')), 2)
                        if abs(je_debit_amount - je_payment_debit_amount) <= 0.5:
                            balance_in = True
                    if balance_in and balance_out:
                        accounting_state = 'balanced'
            else:
                accounting_state = 'balanced'
            rec.accounting_state = accounting_state

    @api.depends('picking_ids')
    def _compute_transfer(self):
        for rec in self:
            rec.transfer_count = len(rec.picking_ids)

    @api.depends('picking_ids')
    def _compute_je(self):
        for rec in self:
            rec.je_count = len(rec._get_journal_entry_count()) or 0

    @api.constrains('crossdock_route_ids')
    def check_crossdock_ids(self):
        for rec in self:
            source_company_ids = rec.crossdock_route_ids.mapped(
                'company_id.id')
            source_warehouse_ids = rec.crossdock_route_ids.mapped(
                'warehouse_id.id')
            dest_company_ids = rec.crossdock_route_ids.mapped(
                'dest_company_id.id')
            dest_warehouse_ids = rec.crossdock_route_ids.sorted(
                lambda cdr_id: cdr_id.sequence).mapped('dest_warehouse_id.id')
            if source_company_ids and rec.company_id.id not in source_company_ids:
                raise ValidationError(_(
                    "First line of Cross dock table should contain Source "
                    "Company %s defined on main form." % rec.company_id.name))
            if dest_company_ids and rec.dest_company_id.id \
                    not in dest_company_ids:
                raise ValidationError(_(
                    "Last line of Cross dock table should contain Final "
                    "Destination Company %s defined on main form." %
                    rec.dest_company_id.name))
            if source_warehouse_ids and rec.warehouse_id.id \
                    not in source_warehouse_ids:
                raise ValidationError(_(
                    "First line of Cross dock table should contain Source "
                    "Warehouse %s defined on main form."
                    % rec.warehouse_id.name))
            if dest_warehouse_ids and (rec.dest_warehouse_id.id
                                       not in dest_warehouse_ids or
                                       rec.dest_warehouse_id.id != dest_warehouse_ids[-1]):
                raise ValidationError(_(
                    "Last line of Cross dock table should contain Final "
                    "Destination Warehouse %s defined on main form." %
                    rec.dest_warehouse_id.name))
            if len(rec.crossdock_route_ids) - len(set(source_warehouse_ids)):
                raise ValidationError(
                    "Source warehouse can't be same for more"
                    " then one cross-dock line.")
            if len(rec.crossdock_route_ids) - len(set(dest_warehouse_ids)):
                raise ValidationError(
                    "Destination warehouse can't be same for"
                    " more then one cross-dock line.")
            source = set(source_warehouse_ids[1:])
            dest = set(dest_warehouse_ids[:-1])
            source_not_found = list(source - dest)
            dest_not_found = list(dest - source)
            if len(source_not_found):
                source_wh_not_found = self.env['stock.warehouse'].browse(
                    source_not_found)
                raise ValidationError(
                    "Source warehouse %s must be present in "
                    "previous line's destination warehouse "
                    % source_wh_not_found.mapped('name'))
            if len(dest_not_found):
                dest_wh_not_found = self.env['stock.warehouse'].browse(
                    dest_not_found)
                raise ValidationError(
                    "Destination warehouse %s must be present "
                    "in next line's source warehouse " %
                    dest_wh_not_found.mapped('name'))

    @api.onchange('transfer_type')
    def onchange_transfer_type(self):
        inter_company_users = self.company_id.inter_company_user_ids
        if not inter_company_users or self.user_id.id not in inter_company_users.ids:
            if self.transfer_type == 'inter_company':
                raise ValidationError(_(
                    F"Please add '{self.user_id.name}' user in Inter Company Users "
                    F"under Settings to perform Inter Company Transfer."))
        self.dest_company_id = False
        self.dest_warehouse_id = False
        self.final_dest_location_id = False

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.warehouse_id = False
        if self.transfer_type == 'inter_company':
            if self.company_id and self.dest_company_id and \
                    self.company_id.id == self.dest_company_id.id:
                raise ValidationError(_(
                    'Source and Destination Company must '
                    'be different'))

    @api.onchange('dest_company_id')
    def onchange_dest_company_id(self):
        self.dest_warehouse_id = False
        if self.transfer_type == 'inter_company':
            if self.company_id and self.dest_company_id and \
                    self.company_id.id == self.dest_company_id.id:
                raise ValidationError(_(
                    'Source and Destination Company must '
                    'be different'))

    @api.onchange('warehouse_id', 'dest_warehouse_id', 'transfer_type')
    def onchange_warehouse(self):
        if self.warehouse_id and self.dest_warehouse_id and \
                self.warehouse_id.id == self.dest_warehouse_id.id and\
                self.transfer_type != 'internal_resupply':
            raise ValidationError(_(
                'Resupply Transfers cannot be created within the same '
                'warehouse. Please select a different warehouse for either '
                'the source or destination, or create an internal transfer.'))
        elif self.warehouse_id and self.dest_warehouse_id and\
                self.warehouse_id.id != self.dest_warehouse_id.id and\
                self.transfer_type == 'internal_resupply':
            self.dest_warehouse_id = self.warehouse_id
        elif self.warehouse_id and not self.dest_warehouse_id and\
                self.transfer_type == 'internal_resupply':
            self.dest_warehouse_id = self.warehouse_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                if 'company_id' in vals:
                    vals['name'] = self.env['ir.sequence'].with_company(
                        vals['company_id']).next_by_code(
                        'inter.company.stock.transfer') or _('New')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'inter.company.stock.transfer') or _('New')
        result = super(InterCompanyStockTransfer, self).create(vals_list)
        return result

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_(
                    'You can not delete a validated Inventory '
                    'Transfer! Try to cancel it before.'))
        return super(InterCompanyStockTransfer, self).unlink()

    def action_view_transfer(self):
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
            action['views'] = [
                (self.env.ref('intercompany_stock_transfer.inter_company_picktree').id, 'tree'),
                (self.env.ref('stock.view_picking_form').id, 'form'),
                (self.env.ref('stock.stock_picking_kanban').id, 'kanban')]
        elif pickings:
            action['views'] = [
                (self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action

    def action_view_journal_entries(self):
        action = self.env.ref(
            'intercompany_stock_transfer.action_move_journal_line_intercompany').read()[0]
        je_records = self._get_journal_entry_count()
        action['domain'] = [('id', 'in', je_records)]
        action['views'] = [
            (self.env.ref(
                'intercompany_stock_transfer.inter_company_journal_entry_tree').id, 'tree'),
            (self.env.ref('account.view_move_form').id, 'form'),
            (self.env.ref('account.view_account_move_kanban').id, 'kanban')]
        return action

    def action_cancel(self):
        self.sudo().mapped('picking_ids').action_cancel()
        self.write({'state': 'cancel'})

    def action_set_draft(self):
        inventory_transfer = self.filtered(lambda rec: rec.state == 'cancel')
        return inventory_transfer.write({'state': 'draft'})

    def _get_journal_entry_count(self):
        for rec in self:
            je_ids = []
            # Payment JE
            payment_list = self.env['account.payment'].search([
                ('stock_transfer_id', '=', rec.id)
            ])
            je_ids.extend(payment_list.mapped('move_id').ids)

            # Transfer's JE
            je_ids.extend(rec.picking_ids.mapped(
                'move_ids').mapped('account_move_ids').ids)

            # Transfer's Invoice JE
            je_ids.extend(rec.picking_ids.mapped(
                'invoice_id').ids)
            return list(set(je_ids))

    def _get_picking_type(self, picking_type, warehouse_id):
        type_obj = self.env['stock.picking.type']
        types = type_obj.sudo().search([
            ('active', '=', True),
            ('code', '=', picking_type),
            ('warehouse_id', '=', warehouse_id)
        ])
        if not types:
            types = type_obj.sudo().search([
                ('active', '=', True),
                ('code', '=', picking_type),
                ('warehouse_id', '=', False)
            ])
        return types[:1]

    def create_delivery_order(
            self, group_id, company_id, warehouse_id, type=None):
        self.ensure_one()
        errors = []
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if type:
            transfer_type = type
        else:
            transfer_type = self.transfer_type
        if transfer_type == 'inter_company':
            property_stock_customer = self.env.ref(
                'stock.stock_location_customers')
        else:
            property_stock_customer = warehouse_id.transit_loc_id
            if not property_stock_customer:
                property_stock_customer = self.env['stock.location'].search([
                    ('company_id', '=', company_id.id),
                    ('usage', '=', 'transit')], order='id', limit=1)
        for line in self.line_ids:
            #             ctx = dict(self._context)
            #             ctx.update({'lot_number': line.lot_id.id,
            #                         'is_intercompany_resupply': True})

            values = line._prepare_procurement_values(
                company_id, warehouse_id, group_id)
            values.update({'stock_transfer_line_id': line})
            values.update({'date': self.scheduled_date})

            product_qty = line.product_uom_qty
            procurement_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            procurements = []
            if procurement_uom.id != quant_uom.id and \
                    get_param('stock.propagate_uom') != '1':
                product_qty, procurement_uom = line.product_uom._adjust_uom_quantities(
                    product_qty, quant_uom)
                # product_qty = line.product_uom._compute_quantity(
                #     product_qty, quant_uom, rounding_method='HALF-UP')
                # procurement_uom = quant_uom
            try:
                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id, product_qty,
                    procurement_uom,
                    property_stock_customer,
                    line.product_id.name, '/',
                    self.env.company, values
                ))
                if procurements:
                    self.env['procurement.group'].run(procurements)

            except UserError as error:
                errors.append(error.args[0])
        return errors

    def create_incoming_shipment(
            self, dest_company_id, dest_warehouse_id,
            type=None, company=None, warehouse=None):
        self.ensure_one()
        StockPicking = self.env['stock.picking']
        if type and company and warehouse:
            transfer_type = type
            company_id = company
            warehouse_id = warehouse
        else:
            transfer_type = self.transfer_type
            company_id = self.company_id
            warehouse_id = self.warehouse_id
        if transfer_type == 'inter_company':
            property_stock_supplier = self.env.ref(
                'stock.stock_location_suppliers').id
        else:
            if warehouse_id.transit_loc_id:
                property_stock_supplier = warehouse_id.transit_loc_id.id
            else:
                transit_location_id = self.env['stock.location'].search([
                    ('company_id', '=', company_id.id),
                    ('usage', '=', 'transit'),
                ], order='id', limit=1)
                property_stock_supplier = transit_location_id and transit_location_id.id

        in_picking_type_id = dest_warehouse_id.in_type_id
        if not in_picking_type_id:
            raise ValidationError(_(
                'Operation type not found for %s' %
                dest_company_id.name))
        location_id = property_stock_supplier
        Push = self.env['stock.rule']
        resupply_transfer = dest_warehouse_id.incoming_route_id or False
        rules = Push.search([
            ('route_id', '=', dest_warehouse_id.incoming_route_id.id)
        ], order='route_sequence, sequence', limit=1)
        if rules:
            if dest_warehouse_id.incoming_route_id and\
                    dest_warehouse_id.incoming_route_id.rule_ids:
                if rules.action == 'push':
                    dest_location_id = rules.location_dest_id.id
                else:
                    dest_location_id = rules.location_src_id.id
            else:
                dest_location_id = rules.location_dest_id.id
        else:
            dest_location_id = in_picking_type_id.default_location_dest_id.id
        in_picking_value = {
            'move_ids': [],
            'state': 'draft',
            'picking_type_id': in_picking_type_id.id,
            'date': self.exp_arrival_date if self.exp_arrival_date else self.scheduled_date,
            'scheduled_date': self.exp_arrival_date if self.exp_arrival_date else self.scheduled_date,
            'origin': self.name,
            'location_dest_id': dest_location_id,
            'location_id': location_id,
            'company_id': dest_company_id.id,
            'partner_id': dest_company_id.partner_id.id,
            'intercom_sale_order_id': self.sale_order_id and self.sale_order_id.id or False
        }
        # Create incoming shipment
        picking = StockPicking.create(in_picking_value)
        moves = self.line_ids._create_stock_moves(
            picking, in_picking_type_id,
            location_id, dest_location_id, dest_company_id)
        moves = moves.filtered(
            lambda x: x.state not in ('done', 'cancel')).with_context(
            resupply_transfer=resupply_transfer)._action_confirm()
        seq = 0
        for move in sorted(moves, key=lambda move: move.date):
            seq += 5
            move.sequence = seq
        picking.message_post_with_view(
            'mail.message_origin_link',
            values={'self': picking, 'origin': self},
            subtype_id=self.env.ref('mail.mt_note').id)
        return True

    def create_internal_resupply_shipment(
            self, dest_company_id, dest_warehouse_id,
            type=None, company=None, warehouse=None):
        self.ensure_one()
        StockPicking = self.env['stock.picking']
        picking_type_id = dest_warehouse_id.pick_type_id or False
        resupply_transfer_type = dest_warehouse_id.int_type_id or False
        if not resupply_transfer_type:
            raise ValidationError(_(
                'Operation type not found for %s' %
                dest_company_id.name))
        location_id = (resupply_transfer_type.default_location_src_id and
                       resupply_transfer_type.default_location_src_id.id or False)
        dest_location_id = self.final_dest_location_id and\
            self.final_dest_location_id.id or False
        in_picking_value = {
            'picking_type_id': resupply_transfer_type.id,
            'date': self.scheduled_date,
            'origin': self.name,
            'location_dest_id': dest_location_id,
            'location_id': location_id,
            'company_id': dest_company_id.id,
            'partner_id': dest_company_id.partner_id.id
        }
        # Create internal transfer
        picking = StockPicking.create(in_picking_value)
        moves = self.line_ids._create_stock_moves(
            picking, resupply_transfer_type,
            location_id, dest_location_id, dest_company_id)

        seq = 0
        for move in sorted(moves, key=lambda move: move.date):
            seq += 5
            move.sequence = seq
        picking.message_post_with_view(
            'mail.message_origin_link',
            values={'self': picking, 'origin': self},
            subtype_id=self.env.ref('mail.mt_note').id)
        return True

    def action_validate(self):
        self.ensure_one()
        self = self.sudo().with_context(tracking_disable=True)
        if not self.exp_arrival_date and self.transfer_type == 'inter_warehouse':
            raise UserError(_("You can not process inventory transfer without adding Expected Arrival Date."))
        if not self.line_ids:
            raise ValidationError(_(
                'You cannot process inventory transfer '
                'without adding product details'))
        location_count = []
        has_zero_qty = False
        for line in self.line_ids:
            if line.location_id:
                if line.location_id.id not in location_count:
                    location_count.append(line.location_id.id)
            if line.product_uom_qty <= 0.0:
                has_zero_qty = True

        if has_zero_qty:
            raise UserError(_(
                'You cannot have zero or negative quantity for product in '
                'inventory transfer lines. Please add correct quantity.'))

        if self.transfer_type == 'internal_resupply':
            if self.final_dest_location_id and\
                    not self.final_dest_location_id.warehouse_id:
                raise UserError(
                    _('Selected Final Destination Location does'
                      ' not belongs to selected warehouse(s).'))
            if self.warehouse_id and self.final_dest_location_id and\
                    self.final_dest_location_id.warehouse_id:
                if self.warehouse_id.id != self.final_dest_location_id.warehouse_id.id:
                    raise UserError(
                        _('Selected Final Destination Location'
                          'does not belongs to selected warehouse(s).'))
        elif self.transfer_type == 'inter_company' and \
                self.company_id == self.dest_company_id:
            raise UserError(
                _('Source and Destination Company must be different'))

        errors = []
        dest_warehouse_id = self.dest_warehouse_id.sudo()
        dest_company_id = self.dest_company_id.sudo()
        group_id = self.group_id
        if not group_id:
            group_id = self.env['procurement.group'].create({
                'name': self.name, 'move_type': 'one',
            })
            self.group_id = group_id.id
        if self.transfer_type == 'inter_warehouse':
            # Create Delivery orders.
            errors += self.create_delivery_order(
                group_id, self.company_id,
                self.warehouse_id)
            # Create Incoming shipment
            self.create_incoming_shipment(
                self.company_id, dest_warehouse_id)
        elif self.transfer_type == 'internal_resupply':
            self.create_internal_resupply_shipment(
                self.company_id, dest_warehouse_id)
        elif self.transfer_type == 'inter_company':
            if self.crossdock_route_ids:
                source_company_ids = self.crossdock_route_ids.mapped(
                    'company_id.id')
                source_warehouse_ids = self.crossdock_route_ids.mapped(
                    'warehouse_id.id')
                dest_company_ids = self.crossdock_route_ids.mapped(
                    'dest_company_id.id')
                dest_warehouse_ids = self.crossdock_route_ids.mapped(
                    'dest_warehouse_id.id')
                if self.company_id.id not in source_company_ids:
                    raise ValidationError(_(
                        "Please define one crossdock line including source "
                        "company %s" % self.company_id.name))
                if self.dest_company_id.id not in dest_company_ids:
                    raise ValidationError(_(
                        "Please define one crossdock line including final "
                        "destination company %s" % self.dest_company_id.name))
                if self.warehouse_id.id not in source_warehouse_ids:
                    raise ValidationError(_(
                        "Please define one crossdock line including source "
                        "Warehouse %s" % self.warehouse_id.name))
                if self.dest_warehouse_id.id not in dest_warehouse_ids:
                    raise ValidationError(_(
                        "Please define one crossdock line including final "
                        "destination warehouse %s" % self.dest_warehouse_id.name))
                for route in self.crossdock_route_ids:
                    if route.transfer_type == 'inter_warehouse':
                        # Create Delivery orders.
                        errors += self.sudo().create_delivery_order(
                            group_id, route.company_id, route.warehouse_id,
                            type=route.transfer_type)

                        # Create Incoming shipment
                        self.sudo().create_incoming_shipment(
                            route.company_id, route.dest_warehouse_id,
                            type=route.transfer_type, company=route.company_id,
                            warehouse=route.warehouse_id)
                    else:
                        # Create Delivery orders.
                        errors += self.sudo().create_delivery_order(
                            group_id, route.company_id, route.warehouse_id,
                            type=route.transfer_type)

                        # Create Incoming shipment
                        self.sudo().create_incoming_shipment(
                            route.dest_company_id, route.dest_warehouse_id,
                            type=route.transfer_type, company=route.company_id,
                            warehouse=route.warehouse_id)
            else:
                # Create Delivery orders.
                errors += self.sudo().create_delivery_order(
                    group_id, self.company_id,
                    self.warehouse_id)

                # Create Incoming shipment
                self.sudo().create_incoming_shipment(
                    dest_company_id,
                    dest_warehouse_id)

        # Link picking with Inventory Transfer
        if not errors:
            pickings = self.env['stock.picking'].search([
                ('group_id', '=', group_id.id)
            ])
            picking_vals = {
                'stock_transfer_id': self.id,
                'intercom_sale_order_id': self.sale_order_id and self.sale_order_id.id or False
            }
            sale_order_id = self.sale_order_id
            if sale_order_id:
                # goflow_routing_status = ""
                # if sale_order_id.goflow_store_id.require_manual_shipment or sale_order_id.goflow_shipment_type in ['ltl','pickup']:
                #     goflow_routing_status = 'require_manual_shipment'
                goflow_order_rec = self.env['goflow.order'].sudo().search([
                    ('sale_order_id', '=', sale_order_id.id)])
                picking_vals.update({
                    'origin': sale_order_id.name,
                    'external_origin': sale_order_id.external_origin,
                    'goflow_customer_name': sale_order_id.goflow_customer_name,                    
                    'goflow_street1': sale_order_id.goflow_street1,
                    'goflow_street2': sale_order_id.goflow_street2,
                    'goflow_city': sale_order_id.goflow_city,
                    'goflow_state': sale_order_id.goflow_state,
                    'goflow_zip_code': sale_order_id.goflow_zip_code,
                    'goflow_country_code': sale_order_id.goflow_country_code,
                    'goflow_shipment_type': sale_order_id.goflow_shipment_type,
                    'goflow_carrier': sale_order_id.goflow_carrier,
                    'goflow_shipping_method': sale_order_id.goflow_shipping_method,
                    'goflow_scac': sale_order_id.goflow_scac,
                    'goflow_shipped_at': sale_order_id.goflow_shipped_at,
                    'goflow_currency_code': sale_order_id.goflow_currency_code,
                    # 'goflow_routing_status': goflow_routing_status,
                    'goflow_order_id': goflow_order_rec and goflow_order_rec.goflow_order_id or False,
                    'goflow_order_no': goflow_order_rec and goflow_order_rec.order_number or False,
                })
                if sale_order_id.goflow_carrier:
                    goflow_carrier = sale_order_id.goflow_carrier
                    # ascii_numbers = string.ascii_letters + string.digits
                    # goflow_carrier = ''.join(c for c in goflow_carrier if c in ascii_numbers).lower()
                    # carrier_ids = self.env['delivery.carrier'].sudo().search([])
                    # carrier_id = False
                    # for carrier in carrier_ids:
                    #     carrier_name = carrier.name
                    #     carrier_name = ''.join(c for c in carrier_name if c in ascii_numbers).lower()
                    #     if goflow_carrier == carrier_name:
                    #         carrier_id = carrier.id
                    carrier_ids = self.env['delivery.carrier'].sudo().search([('carrier_code', '=', goflow_carrier)])
                    carrier_id = False
                    for carrier in carrier_ids:
                        carrier_name = carrier.carrier_code
                        if goflow_carrier == carrier_name:
                            carrier_id = carrier.id
                    picking_vals.update({'carrier_id': carrier_id})
            pickings.write(picking_vals)
        else:
            raise UserError('\n'.join(errors))

        if self.picking_ids:
            stock_transfer_ref = """<a href=# data-oe-model=inter.company.stock.transfer 
                                    data-oe-id=%s>%s</a>""" % (self.id, self.name)
            sale_order_ref = """<a href=# data-oe-model=sale.order 
                                    data-oe-id=%s>%s</a>""" % (self.sale_order_id.id, self.sale_order_id.name)
            picking_sequence = {}
            count = 0
            for picking in self.picking_ids.filtered(
                lambda rec: rec.state not in ('done', 'cancel')
            ).sorted(key=lambda picking: picking.id):
                picking_sequence.update({count: picking})
                if self.sale_order_id:
                    picking.sudo().message_post(
                        body='This transfer has been created through Inter-company stock transfer %s '
                             'for sale order %s' % (stock_transfer_ref, sale_order_ref))
                count += 1
            seq_count = 1
            for seq in picking_sequence:
                if seq_count != len(picking_sequence):
                    next_picking_vals = {'next_picking_id': picking_sequence[seq_count].id}
                    if picking_sequence[seq].picking_type_id.code == 'outgoing':
                        next_picking_vals['next_picking_id'] = self.picking_ids.filtered(
                            lambda p: p.picking_type_id.code == 'incoming')[0].id
                    picking_sequence[seq].write(next_picking_vals)
                    picking_sequence_vals = {'state': 'waiting'}
                    if (picking_sequence[seq].company_id.id != picking_sequence[seq_count].company_id.id or
                            picking_sequence[seq].picking_type_id.code != 'outgoing'):
                        picking_sequence_vals.update({'prev_picking_id': picking_sequence[seq].id})
                    picking_sequence_vals = {
                        'state': 'waiting',
                        'prev_picking_id': picking_sequence[seq].id
                    }
                    if not self.sale_order_id:
                        picking_sequence_vals.update({
                            'origin': picking_sequence[seq].name,
                        })
                    picking_sequence[seq_count].write(picking_sequence_vals)
                seq_count += 1

                if not picking_sequence[seq].prev_picking_id:
                    picking_sequence[seq].move_ids._do_unreserve()

                    trn_location = picking_sequence[seq].stock_transfer_id.parent_location_id
                    if trn_location and trn_location.id != picking_sequence[seq].location_id.id:
                        picking_sequence[seq].location_id = trn_location.id
                        picking_sequence[seq].move_ids.write(
                            {'location_id': trn_location.id})

                    picking_sequence[seq].move_ids._recompute_state()
                    if self.transfer_type == 'inter_warehouse':
                        self.line_ids.create_inter_warehouse_stock_move_lines(picking_sequence[seq])
                    else:
                        self.line_ids._create_stock_move_lines(
                            picking_sequence[seq])
                        picking_sequence[seq].action_assign()

        if self.transfer_type == 'inter_company':
            self.update_warehouse()
        self.update_partner()
        # self.update_location()
        if not self.sale_order_id:
            self.picking_ids.update({'origin': self.name})
        self.write({'state': 'in_progress'})

    def update_location(self):
        location_id = []
        pickings = []
        item_dict = []
        for line in self.line_ids:
            if line.location_id:
                item_dict.append({
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'location_id': line.location_id.id
                })
            elif (line.product_id.nbr_reordering_rules) > 0:
                rr_rule = self.env['stock.warehouse.orderpoint'].search([
                    ('product_id', '=', line.product_id.id),
                    ('warehouse_id', '=', self.warehouse_id.id),
                    ('company_id', '=', self.company_id.id)],
                    order='id ASC', limit=1)
                item_dict.append({
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'location_id': rr_rule.location_id.id
                })
        if item_dict:
            pick_id = self.picking_ids.filtered(
                lambda rec: rec.state not in (
                    'done', 'cancel')).sorted(
                lambda rec: rec.id)[0]
            for move_line in pick_id.move_line_ids:
                for item_data in item_dict:
                    if move_line.product_id.id == item_data.get('product_id') \
                            and item_data.get('location_id', False):
                        move_line.location_id = item_data['location_id']

    def update_warehouse(self):
        for picking in self.picking_ids.sudo():
            if not self.crossdock_route_ids:
                if picking.company_id != picking.stock_transfer_id.company_id:
                    picking.current_pick_warehouse = picking.stock_transfer_id.dest_warehouse_id
                elif picking.company_id == picking.stock_transfer_id.company_id:
                    picking.current_pick_warehouse = picking.stock_transfer_id.warehouse_id
            if self.crossdock_route_ids:
                for crd_line in self.crossdock_route_ids:
                    if picking.company_id == crd_line.company_id and \
                            picking.company_id != crd_line.dest_company_id:
                        picking.current_pick_warehouse = crd_line.warehouse_id
                    elif picking.company_id != crd_line.company_id and \
                            picking.company_id == crd_line.dest_company_id:
                        picking.current_pick_warehouse = crd_line.dest_warehouse_id

    def update_partner(self):
        if self.transfer_type == 'inter_company':
            for line in self.picking_ids.sudo():
                vals = {}
                if line.picking_type_id.code == 'incoming':
                    vals.update({
                        'partner_id': line.prev_picking_id.company_id.partner_id.id,
                    })
                    line.update(vals)
                if line.picking_type_id.code == 'outgoing':
                    vals.update({
                        'partner_id': line.next_picking_id.company_id.partner_id.id})
                    line.update(vals)
                if line.picking_type_id.code == 'internal' and\
                        line.stock_transfer_id and line.next_picking_id:
                    vals.update({
                        'partner_id': self.dest_company_id.partner_id.id
                    })
                    line.update(vals)
                if line.picking_type_id.code == 'internal'\
                        and line.stock_transfer_id \
                        and not line.next_picking_id and line.prev_picking_id:
                    vals.update({
                        'partner_id': self.company_id.partner_id.id
                    })
                    line.update(vals)
        elif self.transfer_type == 'inter_warehouse':
            for picking in self.picking_ids:
                picking.partner_id = self.company_id.partner_id.id
