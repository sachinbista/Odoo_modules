# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class Inventory(models.Model):
    _name = "stock.inventory"
    _inherit = ['stock.inventory', 'mail.thread']


    @api.model
    def default_get(self, fields):
        result = super(Inventory, self).default_get(fields)
        company_id = self.env.user.company_id
        result['adjustment_threshold'] = company_id.adjustment_threshold
        result['first_count_user_ids'] = company_id.first_count_user_ids
        result['second_count_user_ids'] = company_id.second_count_user_ids
        return result

    currency_id = fields.Many2one(
        'res.currency', string="Currency",
        related='company_id.currency_id',
        default=lambda self: self.env.user.company_id.currency_id.id)
    adjustment_threshold = fields.Monetary(
        string="Adjustment Threshold", currency_field='currency_id',
        help="Allow threshold for adjustment, "
             "This value defines threshold for inventory adjustment", tracking=True)
    state = fields.Selection(
        selection_add=[('first_count', 'First Count'), ('second_count', 'Second Count'), ('confirm',)],
        ondelete={'approval': lambda rec: rec.write({'state': 'confirm'})}, tracking=True)
    first_count_user_ids = fields.Many2many(
        'res.users', 'first_count_users_inventory_rel', 'inventory_id', 'user_id',
        string='First Count Users')
    second_count_user_ids = fields.Many2many(
        'res.users', 'second_count_users_inventory_rel', 'inventory_id', 'user_id',
        string='Second Count Users')
    blind_count = fields.Boolean('Is Blind', copy=False, tracking=True)
    line_ids = fields.One2many(
        'stock.inventory.line', 'inventory_id', string='Inventories',
        copy=False, readonly=False,
        states={'done': [('readonly', True)]})
    first_count_user_id = fields.Many2one(
        'res.users', string='First Count User', copy=False, tracking=True)
    second_count_user_id = fields.Many2one(
        'res.users', string='Second Count User', copy=False, tracking=True)
    location_id = fields.Many2one(domain=[('usage', '=', 'internal')], tracking=True)
    access_first_count_qty = fields.Boolean(compute='compute_access_first_count_qty')
    access_second_count_qty = fields.Boolean(compute='compute_access_second_count_qty')
    show_first_count_qty = fields.Boolean(compute='compute_show_first_second_count_qty')
    show_second_count_qty = fields.Boolean(compute='compute_show_first_second_count_qty')

    # Added below fields to add tracking and track the changes.
    name = fields.Char(tracking=True)
    date = fields.Datetime(tracking=True)
    product_id = fields.Many2one(tracking=True)
    package_id = fields.Many2one(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    lot_id = fields.Many2one(tracking=True)
    filter = fields.Selection(tracking=True)
    total_qty = fields.Float(tracking=True)
    category_id = fields.Many2one(tracking=True)
    exhausted = fields.Boolean(tracking=True)


    def compute_access_first_count_qty(self):
        for record in self:
            access_first_count_qty = False
            login_user = self.env.uid
            if login_user in record.first_count_user_ids.ids \
                    and record.state == 'first_count':
                access_first_count_qty = True
            record.access_first_count_qty = access_first_count_qty

    def compute_show_first_second_count_qty(self):
        for record in self:
            show_first_count_qty = False
            show_second_count_qty = False
            login_user = self.env.uid
            first_count_user_ids = record.first_count_user_ids.ids
            second_count_user_ids = record.second_count_user_ids.ids
            if (record.state in ('confirm', 'done') or
                    (login_user in first_count_user_ids or
                     (login_user not in first_count_user_ids and
                      login_user not in second_count_user_ids))):
                show_first_count_qty = True
            if (record.state in ('confirm', 'done') or
                    (login_user in second_count_user_ids or
                     (login_user not in first_count_user_ids and
                      login_user not in second_count_user_ids))):
                show_second_count_qty = True
            record.show_first_count_qty = show_first_count_qty
            record.show_second_count_qty = show_second_count_qty

    def compute_access_second_count_qty(self):
        for record in self:
            access_second_count_qty = False
            login_user = self.env.uid
            if login_user in record.second_count_user_ids.ids \
                    and record.state == 'second_count':
                access_second_count_qty = True
            record.access_second_count_qty = access_second_count_qty

    def action_reset_product_qty(self):
        for record in self:
            if record.state == 'first_count':
                record.mapped('line_ids').write({
                    'product_qty': 0,
                    'first_count_qty': 0
                })
            elif record.state == 'second_count':
                record.mapped('line_ids').write({
                    'second_count_qty': 0
                })
        return True

    def action_start(self):
        super(Inventory, self).action_start()
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            if inventory.filter in ('owner', 'product_owner') and not inventory.partner_id:
                raise ValidationError("Please add Inventoried Owner.")
            elif inventory.filter == 'lot' and not inventory.lot_id:
                raise ValidationError("Please add Inventoried Lot/Serial Number.")
            vals = {'state': 'first_count'}
            inventory.write(vals)
        return True

    def action_submit(self):
        for record in self:
            login_user_id = self.env.uid
            line_ids = record.line_ids
            status = record.state
            values = {}
            if status == 'first_count':
                if login_user_id in record.first_count_user_ids.ids:
                    for line in line_ids:
                        if (line.location_id.usage != 'inventory' and
                                line.product_id.tracking in ('lot', 'serial') and
                                not line.prod_lot_id):
                            raise ValidationError(
                                F"Lot/Serial number is required for the lot/serial "
                                F"tracking product {line.product_id.display_name}.")
                        if (line.location_id.usage != 'inventory' and
                                line.prod_lot_id and line.product_id.tracking == 'serial' and
                                float_compare(abs(line.first_count_qty), 1,
                                              precision_rounding=line.product_uom_id.rounding) > 0):
                            raise ValidationError(
                                _('The serial number has already been assigned: \n Product: %s, Serial Number: %s') % (
                                    line.product_id.display_name, line.prod_lot_id.name))
                        line.product_qty = line.first_count_qty
                    if line_ids.filtered(
                            lambda l:
                            (abs(l.theoretical_qty - l.first_count_qty) * record.product_id.standard_price) >
                            record.adjustment_threshold):
                        status = 'second_count'
                    else:
                        status = 'confirm'
                    values.update({'first_count_user_id': self.env.uid})
                else:
                    raise ValidationError("You are not authorized to perform this operation.")
            elif status == 'second_count':
                if login_user_id in record.second_count_user_ids.ids:
                    for line in line_ids.filtered(lambda l: l.exception):
                        if (line.location_id.usage != 'inventory' and
                                line.product_id.tracking in ('lot', 'serial') and
                                not line.prod_lot_id):
                            raise ValidationError(
                                F"Lot/Serial number is required for the lot/serial "
                                F"tracking product {line.product_id.display_name}.")
                        if (line.location_id.usage != 'inventory' and
                                line.prod_lot_id and line.product_id.tracking == 'serial' and
                                float_compare(abs(line.second_count_qty), 1,
                                              precision_rounding=line.product_uom_id.rounding) > 0):
                            raise ValidationError(
                                _('The serial number has already been assigned: \n Product: %s, Serial Number: %s') % (
                                    line.product_id.display_name, line.prod_lot_id.name))
                        line.product_qty = line.second_count_qty
                    status = 'confirm'
                    values.update({'second_count_user_id': self.env.uid})
                else:
                    raise ValidationError("You are not authorized to perform this operation.")
            values.update({'state': status})
            record.write(values)

    def action_validate(self):
        for record in self:
            for line in record.line_ids:
                line.product_id.inventory_adjustment_date = fields.Datetime.now()
                if (line.product_id.product_tmpl_id and
                        len(line.product_id.product_tmpl_id.product_variant_ids) == 1):
                    line.product_id.product_tmpl_id.inventory_adjustment_date = fields.Datetime.now()
        return super(Inventory, self).action_validate()

    def action_cancel_draft(self):
        for record in self:
            status = 'draft'
            if record.state != 'cancel':
                status = 'cancel'
            record.write({
                'line_ids': [(5,)],
                'state': status,
                'first_count_user_id': False,
                'second_count_user_id': False
            })


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    exception = fields.Boolean(compute='get_exception', string='Exception', store=True)
    first_count_qty = fields.Float(
        'First Count Qty',
        digits='Product Unit of Measure', default=0)
    second_count_qty = fields.Float(
        'Second Count Qty',
        digits='Product Unit of Measure', default=0)
    blind_count = fields.Boolean('Is Blind', related='inventory_id.blind_count', store=True)

    def write(self, values):
        res = super(InventoryLine, self).write(values)
        for record in self:
            record._check_no_duplicate_line()
        return res

    @api.onchange('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id')
    def onchange_get_stock_quant(self):
        self.quant_id = False

    @api.depends('state')
    def get_exception(self):
        for record in self:
            exception = False
            if record.state not in ('draft', 'first_count', 'cancel'):
                if record.state == 'second_count':
                    diff_qty = abs(record.theoretical_qty - record.first_count_qty)
                else:
                    diff_qty = abs(record.theoretical_qty - record.second_count_qty)
                cost_diff = diff_qty * record.product_id.standard_price
                if cost_diff > 0 and cost_diff > record.inventory_id.adjustment_threshold:
                    exception = True
            record.exception = exception
