# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import api, fields, models,exceptions
from datetime import datetime
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    cancel_done_picking = fields.Boolean(string='Cancel Done Delivery?', compute='check_cancel_done_picking')
    picking_code = fields.Selection(string='Code', related='picking_type_id.code')
    returned_ids = fields.Many2many(comodel_name="stock.picking", compute="_compute_returned_ids",
                                    string="Returned pickings")
    total = fields.Float(string='Total Cost', compute='compute_total')
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id', string="Currency", readonly=True)
    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False,
                                help="Date at which the transfer has been processed or cancelled.")

    def compute_total(self):
        for res in self:
            total = 0
            for line in res.move_line_ids_without_package:
                total += line.subtotal
            res.total = total

    # @api.multi
    def _compute_returned_ids(self):
        for picking in self:
            picking.returned_ids = picking.mapped(
                'move_lines.returned_move_ids.picking_id')

    @api.model
    def check_cancel_done_picking(self):

        for picking in self:
            if picking.company_id.cancel_done_picking:
                picking.cancel_done_picking = True
            else:
                picking.cancel_done_picking = False

    def action_view_sale_order(self):
        """This function returns an action that display existing sales order
        of given picking.
        """
        self.ensure_one()
        action = self.env.ref('sale.action_orders').read()[0]
        form = self.env.ref('sale.view_order_form')
        action['views'] = [(form.id, 'form')]
        action['res_id'] = self.sale_id.id
        return action

class StockMove(models.Model):
    _inherit = "stock.move"

    expiry_date = fields.Datetime('Expiry Date', index=True)
    product_vendor_code = fields.Char(string='Vendor Code', compute='get_vendor_code')

    @api.depends()
    def get_vendor_code(self):
        for res in self:
            vendor_code = self.env['product.supplierinfo'].search(
                [('product_tmpl_id', '=', res.product_id.product_tmpl_id.id)], limit=1)
            res.product_vendor_code = vendor_code.product_code


class StockQuant(models.Model):
    _inherit = "stock.quant"

    expiry_date = fields.Datetime('Expiry Date', index=True, readonly=True)
    product_category = fields.Many2one(comodel_name='product.category', related='product_id.categ_id',
                                       string='Category', store=True)

    @api.model
    def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False, src_package_id=False,
                                dest_package_id=False, force_location_from=False, force_location_to=False):
        '''Create a quant in the destination location and create a negative
        quant in the source location if it's an internal location. '''
        price_unit = move.get_price_unit()
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        move_operation = move.picking_id.pack_operation_product_ids.filtered(
            lambda x: x.product_id.id == move.product_id.id and x.qty_done == x.product_qty)
        expiry_date = move_operation[0].expiry_date if move_operation else False

        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'expiry_date': expiry_date,
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
        }
        if move.location_id.usage == 'internal':
            # if we were trying to move something from an internal location and reach here (quant creation),
            # it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.sudo().create(negative_vals)
            vals.update({'propagated_from_id': negative_quant_id.id})

        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (
                not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))

        # create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        return self.sudo().create(vals)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_vendor_code = fields.Char(string='Vendor Code', compute='get_vendor_code')
    cost_price = fields.Float(string='Unit Price', related='move_id.purchase_line_id.price_unit')
    subtotal = fields.Float(string='Subtotal', compute='calc_subtotal')
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id', string="Currency", readonly=True)

    def get_vendor_code(self):
        for res in self:
            vendor_code_variant = self.env['product.supplierinfo'].search([('product_id', '=', res.product_id.id)], limit=1)
            vendor_code_temp = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', res.product_id.product_tmpl_id.id)], limit=1)
            if vendor_code_variant:
                res.product_vendor_code = vendor_code_variant[0].product_code
            elif vendor_code_temp:
                res.product_vendor_code = vendor_code_temp[0].product_code
            else:
                res.product_vendor_code = None

class StockProductionLot(models.Model):
    _inherit = 'stock.lot'

    vendor_id = fields.Many2one(string='Original Vendor',comodel_name='res.partner',compute='get_vendor')

    def get_vendor(self):
        for res in self:
            if res.purchase_order_count > 0:
                res.vendor_id = res.purchase_order_ids[0].partner_id[0].id
            elif len(res.product_id.seller_ids) > 0:
                res.vendor_id = res.product_id.seller_ids[0].name.id

class StockLocationRoute(models.Model):
    _inherit = "stock.route"

    is_maketo_order = fields.Boolean("Is make to order")