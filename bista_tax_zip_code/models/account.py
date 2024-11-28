# -*- encoding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('partner_id', 'partner_shipping_id')
    def _partner_shipping(self):
        tax_id = False
        if not self.partner_id.tax_exemption and self.partner_shipping_id.zip and self.partner_shipping_id.state_id.code and \
                self.invoice_line_ids and self.move_type in ('out_invoice', 'out_refund'):
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
        for line in self.invoice_line_ids:
            if tax_id:
                line.tax_ids = tax_id
            else:
                line.tax_ids = False


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_taxes(self):
        tax_ids = super()._get_computed_taxes()
        for line in self:
            move_id = line.move_id
            if not move_id.partner_id.tax_exemption and move_id.move_type in ('out_invoice', 'out_refund'):
                StateTax = self.env['state.tax']
                AccountTax = self.env['account.tax']
                start_date = datetime.now().date().replace(month=1, day=1)
                end_date = datetime.now().date().replace(month=12, day=31)
                line = line.with_company(line.company_id)
                zip_code = move_id.partner_shipping_id.zip
                state_code = move_id.partner_shipping_id.state_id.code
                state_tax = StateTax.search([
                    ('zip_coe', '=', zip_code), ('start_date', '=', start_date),
                    ('end_date', '=', end_date), ('state_code', '=', state_code)], limit=1
                )
                if state_tax:
                    estimated_county_rate = state_tax.estimated_combined_rate * \
                        float(100)
                    tax_id = AccountTax.search(
                        [('type_tax_use', '=', 'sale'), ('amount', '=', estimated_county_rate)], limit=1)
                    if tax_id:
                        tax_ids = tax_id
            elif move_id.partner_id.tax_exemption:
                partner_exempted_ids = move_id.partner_id.mapped('tax_to_exempted_ids').ids
                product_tax = tax_ids.children_tax_ids.ids
                if any(partner_exempted_ids):
                    tax_to_apply_after_exemption = [i for i in product_tax if i not in partner_exempted_ids]
                    if any(tax_to_apply_after_exemption):
                        tax_ids = self.env['account.tax'].browse(tax_to_apply_after_exemption)
        return tax_ids

    # def _compute_tax_ids(self):
    #     super()._compute_tax_ids()
    #     for line in self:
    #         move_id = line.move_id
    #         if not move_id.partner_id.tax_exemption and not move_id.shopify_order_id and move_id.move_type in ('out_invoice', 'out_refund'):
    #             StateTax = self.env['state.tax']
    #             AccountTax = self.env['account.tax']
    #             start_date = datetime.now().date().replace(month=1, day=1)
    #             end_date = datetime.now().date().replace(month=12, day=31)
    #             line = line.with_company(line.company_id)
    #             zip_code = move_id.partner_shipping_id.zip
    #             state_code = move_id.partner_shipping_id.state_id.code
    #             state_tax = StateTax.search([
    #                 ('zip_coe', '=', zip_code), ('start_date', '=', start_date),
    #                 ('end_date', '=', end_date), ('state_code', '=', state_code)], limit=1
    #             )
    #             if state_tax:
    #                 estimated_county_rate = state_tax.estimated_combined_rate * \
    #                     float(100)
    #                 tax_id = AccountTax.search(
    #                     [('type_tax_use', '=', 'sale'), ('amount', '=', estimated_county_rate)], limit=1)
    #                 if tax_id:
    #                     line.tax_ids = tax_id


class AccountTax(models.Model):
    _inherit = "account.tax"

    is_for_exemption = fields.Boolean(default=False, help="After check this True when we switch to any customer & check Tax Excempt as true this tax would appear for exemption.")