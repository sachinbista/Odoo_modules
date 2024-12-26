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
                    # if any(tax_to_apply_after_exemption):
                    line.tax_id = self.env['account.tax'].browse(tax_to_apply_after_exemption)


    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
                continue
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                line = line.with_company(line.company_id)
                price = line._get_display_price()
                line.price_unit = line.product_id._get_tax_included_unit_price_from_price(
                    price,
                    line.currency_id or line.order_id.currency_id,
                    product_taxes=line.product_id.taxes_id.filtered(
                        lambda tax: tax.company_id == line.env.company
                    ),
                    fiscal_position=line.order_id.fiscal_position_id,
                )
                product_tmpl_id = line.product_id.product_tmpl_id
                taxes = product_tmpl_id.taxes_id.filtered(lambda tax: tax.company_id == line.company_id)
                if line.order_id.partner_id.tax_exemption:
                    partner_exempted_ids = line.order_id.partner_id.mapped('tax_to_exempted_ids').ids
                    tax_exemption = [i for i in taxes.ids if i in partner_exempted_ids]
                    if product_tmpl_id and taxes and tax_exemption:
                        price = product_tmpl_id.list_price
                        res = taxes.compute_all(price, product=product_tmpl_id, partner=self.env['res.partner'], currency = product_tmpl_id.currency_id)
                        excluded = res['total_excluded']
                        line.price_unit = excluded