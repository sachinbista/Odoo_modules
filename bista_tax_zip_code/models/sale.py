# -*- encoding: utf-8 -*-

from odoo import models, api
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('partner_id', 'partner_shipping_id')
    def _partner_shipping(self):
        if not self.partner_id.tax_exemption and self.partner_shipping_id.zip and self.partner_shipping_id.state_id.code and\
                self.order_line:
            StateTax = self.env['state.tax']
            AccountTax = self.env['account.tax']
            start_date = datetime.now().date().replace(month=1, day=1)
            end_date = datetime.now().date().replace(month=12, day=31)
            zip_code = self.partner_shipping_id.zip
            state_code = self.partner_shipping_id.state_id.code
            state_tax = StateTax.search([
                ('zip_coe', '=', zip_code), ('start_date', '=', start_date),
                ('end_date', '=', end_date), ('state_code', '=', state_code)], limit=1
            )
            if state_tax:
                estimated_county_rate = state_tax.estimated_combined_rate * \
                    float(100)
                tax_id = AccountTax.search(
                    [('type_tax_use', '=', 'sale'), ('amount', '=', estimated_county_rate)], limit=1
                )
                if tax_id:
                    self.order_line.write({'tax_id': tax_id})
        else:
            self.order_line.write({'tax_id': False})


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_tax_id(self):
        super()._compute_tax_id()
        for line in self:
            order_id = line.order_id
            if not order_id.partner_id.tax_exemption or order_id.shopify_order_id:
                StateTax = self.env['state.tax']
                AccountTax = self.env['account.tax']
                start_date = datetime.now().date().replace(month=1, day=1)
                end_date = datetime.now().date().replace(month=12, day=31)
                line = line.with_company(line.company_id)
                zip_code = order_id.partner_shipping_id.zip
                state_code = order_id.partner_shipping_id.state_id.code
                state_tax = StateTax.search([
                    ('zip_coe', '=', zip_code), ('start_date', '=', start_date),
                    ('end_date', '=', end_date), ('state_code', '=', state_code)], limit=1)
                if state_tax:
                    estimated_county_rate = state_tax.estimated_combined_rate * \
                        float(100)
                    tax_id = AccountTax.search(
                        [('type_tax_use', '=', 'sale'), ('amount', '=', estimated_county_rate)], limit=1
                    )
                    if tax_id:
                        line.tax_id = tax_id
            elif order_id.partner_id.tax_exemption:
                partner_exempted_ids = order_id.partner_id.mapped('tax_to_exempted_ids').ids
                product_tax = line.mapped('tax_id').ids
                if any(partner_exempted_ids):
                    tax_to_apply_after_exemption = [i for i in product_tax if i not in partner_exempted_ids]
                    if any(tax_to_apply_after_exemption):
                        line.tax_id = self.env['account.tax'].browse(tax_to_apply_after_exemption)
