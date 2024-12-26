# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import AND
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class ShippingManifestBatch(models.Model):
    _name = "shipping.manifest.batch"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Shipping Manifest Batch Transfer"
    _order = "name desc"


    name = fields.Char(
        string='Batch Transfer', default='New',
        copy=False, required=True, readonly=True)

    user_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True,
        states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(
        'res.company', string="Company", required=True, readonly=True,
        index=True, default=lambda self: self.env.company)
    picking_ids = fields.One2many(
        'stock.picking', 'shipping_batch_id', string='Transfers', readonly=True,
        domain="[('id', 'in', allowed_picking_ids)]", check_company=True,
        states={'draft': [('readonly', False)], 'in_progress': [('readonly', False)]},
        help='List of transfers associated to this batch')
    show_check_availability = fields.Boolean(
        compute='_compute_move_ids',
        string='Show Check Availability')
    show_validate = fields.Boolean(
        compute='_compute_show_validate',
        string='Show Validate Button')
    show_allocation = fields.Boolean(
        compute='_compute_show_allocation',
        string='Show Allocation Button')
    allowed_picking_ids = fields.One2many('stock.picking', compute='_compute_allowed_picking_ids')
    is_wave = fields.Boolean('This batch is a wave')
    move_ids = fields.One2many(
        'stock.move', string="Stock moves", compute='_compute_move_ids')
    move_line_ids = fields.One2many(
        'stock.move.line', string='Stock move lines',
        compute='_compute_move_ids', inverse='_set_move_line_ids', readonly=True,
        states={'draft': [('readonly', False)], 'in_progress': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='draft',
        store=True, compute='_compute_state',
        copy=False, tracking=True, required=True, readonly=True, index=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', check_company=True, copy=False,
        readonly=True, index=True, states={'draft': [('readonly', False)]})

    picking_type_code = fields.Selection(
        related='picking_type_id.code')
    scheduled_date = fields.Datetime(
        'Scheduled Date', copy=False, store=True, readonly=False, compute="_compute_scheduled_date",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="""Scheduled date for the transfers to be processed.
                  - If manually set then scheduled date for all transfers in batch will automatically update to this date.
                  - If not manually changed and transfers are added/removed/updated then this will be their earliest scheduled date
                    but this scheduled date will not be set for all transfers in batch.""")
    show_set_qty_button = fields.Boolean(compute='_compute_show_qty_button')
    show_clear_qty_button = fields.Boolean(compute='_compute_show_qty_button')
    show_lots_text = fields.Boolean(compute='_compute_show_lots_text')

    # -------------------------------------------------------------------------
    # Miscellaneous
    # -------------------------------------------------------------------------
    def _sanity_check(self):
        for batch in self:
            if not batch.picking_ids <= batch.allowed_picking_ids:
                erroneous_pickings = batch.picking_ids - batch.allowed_picking_ids
                raise UserError(_(
                    "The following transfers cannot be added to batch transfer %s. "
                    "Please check their states and operation types, if they aren't immediate "
                    "transfers.\n\n"
                    "Incompatibilities: %s", batch.name, ', '.join(erroneous_pickings.mapped('name'))))

    def _track_subtype(self, init_values):
        if 'state' in init_values:
            return self.env.ref('shipping_manifest_batch.mt_shipping_manifest_batch_state')
        return super()._track_subtype(init_values)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_done(self):
        if any(batch.state == 'done' for batch in self):
            raise UserError(_("You cannot delete Done batch transfers."))

    # def _is_picking_auto_mergeable(self, picking):
    #     """ Verifies if a picking can be safely inserted into the batch without violating auto_batch_constrains.
    #     """
    #     res = True
    #     if self.picking_type_id.batch_max_lines:
    #         res = res and (len(self.move_ids) + len(picking.move_ids) <= self.picking_type_id.batch_max_lines)
    #     if self.picking_type_id.batch_max_pickings:
    #         res = res and (len(self.picking_ids) + 1 <= self.picking_type_id.batch_max_pickings)
    #     return res


    # def write(self, vals):
    #     res = super().write(vals)
    #     if not self.picking_ids:
    #         self.filtered(lambda b: b.state == 'in_progress').action_cancel()
    #     # if vals.get('picking_type_id'):
    #     #     self._sanity_check()
    #     if vals.get('picking_ids'):
    #         batch_without_picking_type = self.filtered(lambda batch: not batch.picking_type_id)
    #         if batch_without_picking_type:
    #             picking = self.picking_ids and self.picking_ids[0]
    #             batch_without_picking_type.picking_type_id = picking.picking_type_id.id
    #     if vals.get('user_id'):
    #         self.picking_ids.assign_batch_user(vals['user_id'])
    #     return res

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """Sanity checks, confirm the pickings and mark the batch as confirmed."""
        # self.ensure_one()
        for picking in self.picking_ids:
            if picking.state not in ('done','cancel'):
                raise UserError(_("pickings are not in done or cancel."))
        # if not self.picking_ids:
        #     raise UserError(_("You have to set some pickings to batch."))
        # self.picking_ids.action_confirm()
        # self._check_company()
        self.state = 'done'
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company_id = vals.get('company_id', self.env.company.id)
                if vals.get('is_wave'):
                    vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code('shipping.wave') or '/'
                else:
                    vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code('shipping.batch') or '/'
        return super().create(vals_list)

    # def action_done(self):
    #     def has_no_qty_done(picking):
    #         return all(float_is_zero(line.qty_done, precision_rounding=line.product_uom_id.rounding) for line in picking.move_line_ids if line.state not in ('done', 'cancel'))
    #
    #     self.ensure_one()
    #     self._check_company()
    #     # Empty 'waiting for another operation' pickings will be removed from the batch when it is validated.
    #     pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state not in ('cancel', 'done'))
    #     empty_waiting_pickings = self.mapped('picking_ids').filtered(lambda p: p.state == 'waiting' and has_no_qty_done(p))
    #     pickings = pickings - empty_waiting_pickings
    #
    #     empty_pickings = set()
    #     for picking in pickings:
    #         if has_no_qty_done(picking):
    #             empty_pickings.add(picking.id)
    #         picking.message_post(
    #             body="<b>%s:</b> %s <a href=#id=%s&view_type=form&model=shipping.manifest.batch>%s</a>" % (
    #                 _("Transferred by"),
    #                 _("Batch Transfer"),
    #                 picking.shipping_batch_id.id,
    #                 picking.shipping_batch_id.name))
    #
    #     # Run sanity_check as a batch and ignore the one in button_validate() since it is done here.
    #     pickings._sanity_check(separate_pickings=False)
    #     # Skip sanity_check in pickings button_validate() & remove 'waiting' pickings from the batch
    #     context = {'skip_sanity_check': True, 'pickings_to_detach': empty_waiting_pickings.ids}
    #     if len(empty_pickings) == len(pickings):
    #         return pickings.with_context(**context).button_validate()
    #     else:
    #         # If some pickings are at least partially done, other pickings (empty & waiting) will be removed from batch without being cancelled in case of no backorder
    #         pickings = pickings - self.env['stock.picking'].browse(empty_pickings)
    #         context['pickings_to_detach'] = context['pickings_to_detach'] + list(empty_pickings)
    #         return pickings.with_context(skip_immediate=True, **context).button_validate()

    # def action_assign(self):
    #     self.ensure_one()
    #     self.picking_ids.action_assign()





    @api.depends('picking_type_id')
    def _compute_show_lots_text(self):
        for batch in self:
            batch.show_lots_text = batch.picking_ids and batch.picking_ids[0].show_lots_text


    def action_cancel(self):
        self.state = 'cancel'
        self.picking_ids = False
        return True

    @api.depends('state', 'show_validate',
                 'picking_ids.show_set_qty_button',
                 'picking_ids.show_clear_qty_button')
    def _compute_show_qty_button(self):
        self.show_set_qty_button = False
        self.show_clear_qty_button = False
        for batch in self:
            if not batch.show_validate or batch.state != 'in_progress':
                continue
            if any(p.show_set_qty_button for p in self.picking_ids):
                batch.show_set_qty_button = True
            elif any(p.show_clear_qty_button for p in self.picking_ids):
                batch.show_clear_qty_button = True

    @api.depends('picking_ids', 'picking_ids.move_line_ids', 'picking_ids.move_ids', 'picking_ids.move_ids.state')
    def _compute_move_ids(self):
        for batch in self:
            batch.move_ids = batch.picking_ids.move_ids
            batch.move_line_ids = batch.picking_ids.move_line_ids
            batch.show_check_availability = any(m.state not in ['assigned', 'done'] for m in batch.move_ids)


    @api.depends('picking_ids', 'picking_ids.show_validate')
    def _compute_show_validate(self):
        for batch in self:
            batch.show_validate = any(picking.show_validate for picking in batch.picking_ids)

    @api.depends('state', 'move_ids', 'picking_type_id')
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.user_has_groups('stock.group_reception_report'):
            return
        for batch in self:
            batch.show_allocation = batch.picking_ids._get_show_allocation(batch.picking_type_id)

    @api.depends('company_id', 'picking_type_id', 'state')
    def _compute_allowed_picking_ids(self):
        allowed_picking_states = ['waiting', 'confirmed', 'assigned','done','cancel']

        for batch in self:
            domain_states = list(allowed_picking_states)
            # Allows to add draft pickings only if batch is in draft as well.
            if batch.state == 'draft':
                domain_states.append('draft')
            domain = [
                ('company_id', '=', batch.company_id.id),
                ('state', 'in', domain_states),
            ]
            if not batch.is_wave:
                domain = AND([domain, [('immediate_transfer', '=', False)]])
            if batch.picking_type_id:
                domain += [('picking_type_id', '=', batch.picking_type_id.id)]
            batch.allowed_picking_ids = self.env['stock.picking'].search(domain)

    def _set_move_line_ids(self):
        new_move_lines = self[0].move_line_ids
        for picking in self.picking_ids:
            old_move_lines = picking.move_line_ids
            picking.move_line_ids = new_move_lines.filtered(lambda ml: ml.picking_id.id == picking.id)
            move_lines_to_unlink = old_move_lines - new_move_lines
            if move_lines_to_unlink:
                move_lines_to_unlink.unlink()

    # @api.depends('picking_ids', 'picking_ids.state')
    # def _compute_state(self):
    #     batchs = self.filtered(lambda batch: batch.state not in ['cancel', 'done'])
    #     for batch in batchs:
    #         if not batch.picking_ids:
    #             continue
    #         # Cancels automatically the batch picking if all its transfers are cancelled.
    #         if all(picking.state == 'cancel' for picking in batch.picking_ids):
    #             batch.state = 'cancel'
    #         # Batch picking is marked as done if all its not canceled transfers are done.
    #         elif all(picking.state in ['cancel', 'done'] for picking in batch.picking_ids):
    #             batch.state = 'done'

    @api.depends('picking_ids', 'picking_ids.scheduled_date')
    def _compute_scheduled_date(self):
        for rec in self:
            rec.scheduled_date = min(rec.picking_ids.filtered('scheduled_date').mapped('scheduled_date'), default=False)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipping_batch_id = fields.Many2one(
        'shipping.manifest.batch', string='Batch Transfer',
        check_company=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Batch associated to this transfer', index=True, copy=False)

