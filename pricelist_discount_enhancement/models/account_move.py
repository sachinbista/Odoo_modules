# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'


    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        compute='_compute_pricelist_id',
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")

    tax_id = fields.Many2one('account.tax', string='Tax')

    @api.model_create_multi
    def create(self,vals_list):
        for vals in vals_list:
            if vals.get("partner_shipping_id"):
                partner_shipping_id = self.env['res.partner'].browse(vals.get("partner_shipping_id"))
                if partner_shipping_id.country_id:
                    country_tax_id = self.env['country.tax'].search([('country_id', '=', partner_shipping_id.country_id.id)],limit=1)
                    if country_tax_id:
                        vals['tax_id'] = country_tax_id.tax_id.id
        return super(AccountMove, self).create(vals_list)

    @api.depends('partner_id', 'company_id')
    def _compute_pricelist_id(self):
        for order in self:
            if order.state != 'draft' or order.move_type not in ['out_invoice', 'out_refund']:
                continue
            if not order.partner_id:
                order.pricelist_id = False
                continue
            order = order.with_company(order.company_id)
            order.pricelist_id = order.partner_id.property_product_pricelist

    def action_update_prices(self):
        self.ensure_one()
        is_tax_exempt = False
        if self.tax_id:
            is_tax_exempt = True
        for line in self.invoice_line_ids:
            pricelist = self.env['product.pricelist'].browse(line.move_id.pricelist_id.id)
            if pricelist:
                product_price = pricelist._get_product_price(line.product_id,line.quantity)
                if is_tax_exempt:
                    tax_amount = (self.tax_id.amount/100)+1
                    line.price_unit = (product_price/tax_amount)
