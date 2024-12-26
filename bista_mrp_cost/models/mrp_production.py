# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    mrp_labor_cost = fields.Float(string="Labor Cost")
    mrp_labor_account = fields.Many2one("account.account", string="Labor Account")
    mrp_overhead_cost = fields.Float(string="Overhead Cost")
    mrp_overhead_account = fields.Many2one("account.account", string="Overhead Account")

    def button_mark_done(self):
        ret = super(MrpProduction, self).button_mark_done()
        for rec in self:
            if rec.state == 'done' and rec.bom_id and rec.bom_id.type == 'normal':
                rec._save_costing_info()
                rec._apply_labor_cost()
                rec._apply_overhead_cost()
        return ret

    def _save_costing_info(self):
        bom = self.bom_id
        company = self.env.company
        self.write({
            'mrp_labor_cost': bom.mrp_labor_cost or company.mrp_labor_cost,
            'mrp_labor_account': bom.mrp_labor_account.id or company.mrp_labor_account.id,
            'mrp_overhead_cost': bom.mrp_overhead_cost or company.mrp_overhead_cost,
            'mrp_overhead_account': bom.mrp_overhead_account.id or company.mrp_overhead_account.id,
        })

    def _apply_labor_cost(self):
        production_ref = self.display_name
        labor_cost = self.mrp_labor_cost * self.product_qty
        labor_account = self.mrp_labor_account

        if labor_cost and not labor_account:
            raise UserError(
                "No account is provided for labor cost. Either assign the account on the bom or in the settings.")
        ref = "%s - %s" % (production_ref, "Labor Cost")
        self._revaluate_product(ref, labor_cost, labor_account)

    def _apply_overhead_cost(self):
        production_ref = self.display_name
        overhead_cost = self.mrp_overhead_cost * self.product_qty
        overhead_account = self.mrp_overhead_account

        if overhead_cost and not overhead_account:
            raise UserError(
                "NO account is provided for overhead cost. Either assign the account on the bom or in the settings.")
        # Generate labor Cost
        ref = "%s - %s" % (production_ref, "Overhead Cost")
        self._revaluate_product(ref, overhead_cost, overhead_account)

    def _revaluate_product(self, description, added_value, account):
        if not added_value or not account:
            return

        self.ensure_one()
        product_id = self.product_id.with_company(self.env.company)

        remaining_svls = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product_id.id),
            ('company_id', '=', self.env.company.id),
        ], order="id desc")

        remaining_qty = sum(line.quantity for line in remaining_svls)
        remaining_value = added_value + sum(line.value for line in remaining_svls)

        # Create a manual stock valuation layer
        revaluation_svl_vals = {
            'company_id': self.env.company.id,
            'product_id': product_id.id,
            'description': description,
            'value': added_value,
            'quantity': 0,
            'remaining_value': remaining_value,
            'remaining_qty': remaining_qty
        }

        revaluation_svl = self.env['stock.valuation.layer'].create(revaluation_svl_vals)

        # Update the standard price in case of AVCO
        if product_id.categ_id.property_cost_method == 'average':
            product_id.with_context(disable_auto_svl=True).standard_price = (remaining_value / (remaining_qty or 1))

        accounts = product_id.product_tmpl_id.get_product_accounts()
        valuation_account = accounts.get('stock_valuation') and accounts['stock_valuation'].id

        if added_value < 0:
            debit_account_id = account.id
            credit_account_id = valuation_account
        else:
            debit_account_id = valuation_account
            credit_account_id = account.id

        analytic_account = self.analytic_account_id.id
        move_vals = {
            'journal_id': accounts['stock_journal'].id,
            'company_id': self.env.company.id,
            'ref': description,
            'stock_valuation_layer_ids': [(6, None, [revaluation_svl.id])],
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': description,
                'account_id': debit_account_id,
                'debit': abs(added_value),
                'credit': 0,
                'product_id': product_id.id,
                'analytic_account_id': analytic_account
            }), (0, 0, {
                'name': description,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(added_value),
                'product_id': product_id.id,
                'analytic_account_id': analytic_account
            })],
        }

        account_move = self.env['account.move'].sudo().create(move_vals)
        account_move._post()

        if analytic_account:
            analytic_line_vals = {'name': description,
                                  'amount': -abs(added_value),
                                  'account_id': analytic_account,
                                  'unit_amount': 1,
                                  'product_id': product_id.id,
                                  'product_uom_id': product_id.uom_id.id,
                                  'company_id': self.env.company.id,
                                  'category': 'manufacturing_order'}
            self.env['account.analytic.line'].sudo().create(analytic_line_vals)
        return
