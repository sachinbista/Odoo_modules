# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, fields, models, _
from datetime import datetime
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class UpdateSaleOrder(models.TransientModel):
    _name = 'update.saleorder'
    _description = "Update Sale Order"

    new_order_line_ids = fields.One2many('getsale.orderdata', 'new_order_line_id', string="Order Line")
    line_id = fields.Many2one('sale.order.line',string='Line')

    @api.model
    def default_get(self, default_fields):
        res = super(UpdateSaleOrder, self).default_get(default_fields)
        sale_id = self.env['sale.order'].browse(self._context.get('active_ids', []))
        credit_manager_group = self.env.user.has_group('bista_customer_credit_limit.customer_credit_limit_manager')
        update = []
        for record in sale_id.order_line:
            update.append((0, 0, {
                'product_id': record.product_id.id,
                'name': record.name,
                'product_qty': record.product_uom_qty,
                'price_unit': record.price_unit,
                'line_id':record.id,
            }))
        res.update({'new_order_line_ids': update})
        return res

    def _compute_credit_threshold(self):
        self._compute_credit_warning_threshold()
        self._compute_credit_blocking_threshold()

    @api.depends('new_order_line_ids')
    def _compute_credit_blocking_threshold(self):
        partner_id = self._context.get('partner_id')
        for x in self:
            total_credit_sale = sum(line.product_subtotal for line in x.new_order_line_ids)
            partner_id.credit_blocking_threshold = partner_id.credit_blocking - total_credit_sale if partner_id.credit_blocking else 0

    @api.depends('new_order_line_ids')
    def _compute_credit_warning_threshold(self):
        partner_id = self._context.get('partner_id')
        for x in self:
            total_credit_sale = sum(line.product_subtotal for line in x.new_order_line_ids)
            partner_id.credit_warning_threshold = partner_id.credit_warning - total_credit_sale if partner_id.credit_warning else 0

    def action_update_order_line(self):
        context = dict(self.env.context or {})
        sale_blocking_message = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_blocking_message')
        sale_warning_message = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_waring_message')
        sale_id = self.env['sale.order'].browse(self._context.get('active_ids', []))
        sum = 0.0
        for data in self.new_order_line_ids:
            sum += data.product_qty * data.price_unit
        self.with_context(partner_id=sale_id.partner_id)._compute_credit_threshold()
        if sale_id.partner_id.credit_warning_threshold <= 0 and sale_id.partner_id.credit_blocking_threshold >= 0:
            if sale_id.partner_id.credit_warning_message:
                context['message'] = (
                            sale_id.partner_id.credit_warning_message or "Customer credit limit exceeded, Want to continue?")
                context['new_order_line_ids'] = self.new_order_line_ids
            else:
                context['message'] = sale_warning_message or "Customer credit limit exceeded, Want to continue?"
                context['new_order_line_ids'] = self.new_order_line_ids
        if sale_id.partner_id.credit_blocking_threshold <=0:
            if sale_id.partner_id.credit_blocking_message:
                context['message'] = (sale_id.partner_id.credit_blocking_message or "Customer credit limit exceeded, Want to continue?")
                context['new_order_line_ids'] = self.new_order_line_ids
            else:
                context['message'] = sale_blocking_message or "Customer credit limit exceeded, Want to continue?"
                context['new_order_line_ids'] = self.new_order_line_ids

        if sale_id.partner_id.credit_blocking_threshold < 0 or sale_id.partner_id.credit_warning_threshold < 0:
            view_id = self.env.ref('bista_customer_credit_limit.view_blocking_wizard_warning_form')
            return {
                'name': 'Warning/Blocking  Limit',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'wizard.block',
                'view_id': view_id.id,
                'target': 'new',
                'context': context,
            }
        else:
            for line in self.new_order_line_ids:
                order_line = self.env['sale.order.line'].search([('id', '=', line.line_id.id)])
                if order_line:
                    order_line.order_id.flag = False
                    order_line.write({
                        'product_uom_qty': line.product_qty,
                        'price_unit': line.price_unit,
                    })

class Getsaleorderdata(models.TransientModel):
    _name = 'getsale.orderdata'
    _description = "Get Sale Order Data"

    new_order_line_id = fields.Many2one('update.saleorder')

    product_id = fields.Many2one('product.product', string="Product", required=True)
    name = fields.Char(string="Description")
    product_qty = fields.Float(string='Quantity', required=True)
    date_planned = fields.Datetime(string='Scheduled Date', default=datetime.today())
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure')
    order_id = fields.Many2one('sale.order', string='Order Reference', ondelete='cascade', index=True)
    price_unit = fields.Float(string='Unit Price')
    product_subtotal = fields.Float(string="Sub Total", compute='_compute_total')
    line_id = fields.Many2one('sale.order.line', required=True)
    group_id = fields.Many2one('res.groups')

    @api.depends('product_qty', 'price_unit')
    def _compute_total(self):
        for record in self:
            record.product_subtotal = record.product_qty * record.price_unit

