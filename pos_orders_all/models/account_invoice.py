# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from functools import partial
from odoo.tools import frozendict, formatLang, format_date, float_is_zero
import psycopg2
import pytz
from odoo.tools.misc import formatLang
from odoo import api, fields, models, tools, _, Command
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
import odoo.addons.decimal_precision as dp
from functools import partial

_logger = logging.getLogger(__name__)


class AccountInvoiceInherit(models.Model):
	_inherit = "account.move"

	pos_order_id = fields.Many2one('pos.order', string="POS order")
	discount_amt = fields.Float('Discount Final Amount')
	discount_amount = fields.Float('Discount Amount')
	discount_amount_line = fields.Monetary(string="Discount Line")
	config_inv_tax = fields.Monetary(string="total disc tax",compute="_calculate_discount",store=True)

	def _calculate_discount(self):
		res_config= self.env.company
		cur_obj = self.env['res.currency']
		res=0.0
		discount = 0.0
		for move in self:
			applied_discount = line_discount = sums = move_discount =  amount_untaxed = amount_tax = amount_after_discount =  0.0
			for line in move.invoice_line_ids:
				amount_untaxed += line.price_subtotal
				amount_tax += abs(line.price_subtotal - line.price_total)
				applied_discount += line.discount_amt
				if line.discount_line_type == 'Fixed':
					res += line.discount
				elif line.discount_line_type == 'Percentage':
					res += line.price_subtotal * (line.discount/ 100)
		return res


	@api.depends(
		'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
		'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
		'line_ids.balance',
		'line_ids.currency_id',
		'line_ids.amount_currency',
		'line_ids.amount_residual',
		'line_ids.amount_residual_currency',
		'line_ids.payment_id.state',
		'line_ids.full_reconcile_id','line_ids.discount_line_type','line_ids.discount')
	def _compute_amount(self):
		for move in self:
			total_untaxed, total_untaxed_currency = 0.0, 0.0
			total_tax, total_tax_currency = 0.0, 0.0
			total_residual, total_residual_currency = 0.0, 0.0
			total, total_currency = 0.0, 0.0

			for line in move.line_ids:
				if move.is_invoice(True):
					# === Invoices ===
					if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
						# Tax amount.
						total_tax += line.balance
						total_tax_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.display_type in ('product', 'rounding'):
						# Untaxed amount.
						total_untaxed += line.balance
						total_untaxed_currency += line.amount_currency
						total += line.balance
						total_currency += line.amount_currency
					elif line.display_type == 'payment_term':
						# Residual amount.
						total_residual += line.amount_residual
						total_residual_currency += line.amount_residual_currency
				else:
					# === Miscellaneous journal entry ===
					if line.debit:
						total += line.balance
						total_currency += line.amount_currency

			sign = move.direction_sign
			move.amount_untaxed = sign * total_untaxed_currency
			move.amount_tax = sign * total_tax_currency
			move.amount_total = sign * total_currency
			move.amount_residual = -sign * total_residual_currency
			move.amount_untaxed_signed = -total_untaxed
			move.amount_tax_signed = -total_tax
			move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
			move.amount_residual_signed = total_residual
			move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)
			res = move._calculate_discount()
			move.discount_amt = res



class AccountTax(models.Model):
	_inherit = "account.tax"

	@api.model
	def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
		
		obj_name = base_line['record']
		if 'discount_line_type' in obj_name._fields:
			if obj_name.discount_line_type == 'Fixed':
				orig_price_unit_after_discount = base_line['price_unit'] - (base_line['discount'])
			else:
				orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
		else:
			orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))

		price_unit_after_discount = orig_price_unit_after_discount
		taxes = base_line['taxes']._origin
		currency = base_line['currency'] or self.env.company.currency_id
		rate = base_line['rate']

		if early_pay_discount_computation in ('included', 'excluded'):
			remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
			price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

		if taxes:

			if handle_price_include is None:
				manage_price_include = bool(base_line['handle_price_include'])
			else:
				manage_price_include = handle_price_include

			taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
				price_unit_after_discount,
				currency=currency,
				quantity=base_line['quantity'],
				product=base_line['product'],
				partner=base_line['partner'],
				is_refund=base_line['is_refund'],
				handle_price_include=manage_price_include,
				include_caba_tags=include_caba_tags,
			)

			to_update_vals = {
				'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
				'price_subtotal': taxes_res['total_excluded'],
				'price_total': taxes_res['total_included'],
			}

			if early_pay_discount_computation == 'excluded':
				new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
					orig_price_unit_after_discount,
					currency=currency,
					quantity=base_line['quantity'],
					product=base_line['product'],
					partner=base_line['partner'],
					is_refund=base_line['is_refund'],
					handle_price_include=manage_price_include,
					include_caba_tags=include_caba_tags,
				)
				for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
					delta_tax = new_taxes_res['amount'] - tax_res['amount']
					tax_res['amount'] += delta_tax
					to_update_vals['price_total'] += delta_tax

			tax_values_list = []
			for tax_res in taxes_res['taxes']:
				tax_amount = tax_res['amount'] / rate
				if self.company_id.tax_calculation_rounding_method == 'round_per_line':
					tax_amount = currency.round(tax_amount)
				tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
				tax_values_list.append({
					**tax_res,
					'tax_repartition_line': tax_rep,
					'base_amount_currency': tax_res['base'],
					'base_amount': currency.round(tax_res['base'] / rate),
					'tax_amount_currency': tax_res['amount'],
					'tax_amount': tax_amount,
				})

		else:
			price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
			to_update_vals = {
				'tax_tag_ids': [Command.clear()],
				'price_subtotal': price_subtotal,
				'price_total': price_subtotal,
			}
			tax_values_list = []

		return to_update_vals, tax_values_list


	
class AccountInvoiceLineInherit(models.Model):
	_inherit = "account.move.line"

	pos_order_id = fields.Many2one('pos.order', string="POS order")
	pos_order_line_id = fields.Many2one('pos.order.line', string="POS order Line")
	discount_line_type = fields.Char(related='pos_order_line_id.discount_line_type', string='Discount Type',
									 readonly=True, store=True)
	discount_amt = fields.Float('Discount Final Amount')
	discount_amount = fields.Float('Discount Amount')


	@api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id', 'move_id.partner_id', 'price_unit')
	def _compute_all_tax(self):
		for line in self:
			sign = line.move_id.direction_sign
			if line.display_type == 'tax':
				line.compute_all_tax = {}
				line.compute_all_tax_dirty = False
				continue
			if line.display_type == 'product' and line.move_id.is_invoice(True):
				if line.discount_line_type and line.discount_line_type == "Fixed":
					amount_currency = sign * (line.price_unit - line.discount)
				else:
					amount_currency = sign * line.price_unit * (1 - (line.discount / 100.0))
					
				# amount_currency = sign * line.price_unit * (1 - line.discount / 100)
				handle_price_include = True
				quantity = line.quantity
			else:
				amount_currency = line.amount_currency
				handle_price_include = False
				quantity = 1
			compute_all_currency = line.tax_ids.compute_all(
				amount_currency,
				currency=line.currency_id,
				quantity=quantity,
				product=line.product_id,
				partner=line.move_id.partner_id or line.partner_id,
				is_refund=line.is_refund,
				handle_price_include=handle_price_include,
				include_caba_tags=line.move_id.always_tax_exigible,
				fixed_multiplicator=sign,
			)
			rate = line.amount_currency / line.balance if line.balance else 1
			line.compute_all_tax_dirty = True

			line.compute_all_tax = {
				frozendict({
					'tax_repartition_line_id': tax['tax_repartition_line_id'],
					'group_tax_id': tax['group'] and tax['group'].id or False,
					'account_id': tax['account_id'] or line.account_id.id,
					'currency_id': line.currency_id.id,
					'analytic_distribution': (tax['analytic'] or not tax['use_in_tax_closing']) and line.analytic_distribution,
					'tax_ids': [(6, 0, tax['tax_ids'])],
					'tax_tag_ids': [(6, 0, tax['tag_ids'])],
					'partner_id': line.move_id.partner_id.id or line.partner_id.id,
					'move_id': line.move_id.id,
				}): {
					'name': tax['name'],
					'balance': tax['amount'] / rate,
					'amount_currency': tax['amount'],
					'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
				}
				for tax in compute_all_currency['taxes']
				if tax['amount']
			}
			if not line.tax_repartition_line_id:
				line.compute_all_tax[frozendict({'id': line.id})] = {
					'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
				}


	@api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
	def _compute_totals(self):
		for line in self:
			if line.display_type != 'product':
				line.price_total = line.price_subtotal = False

			if line.discount_line_type and line.discount_line_type == "Fixed":
				line_discount_price_unit = line.price_unit - line.discount
			else:
				line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))


			subtotal = line.quantity * line_discount_price_unit

			# Compute 'price_total'.
			if line.tax_ids:
				taxes_res = line.tax_ids.compute_all(
					line_discount_price_unit,
					quantity=line.quantity,
					currency=line.currency_id,
					product=line.product_id,
					partner=line.partner_id,
					is_refund=line.is_refund,
				)
				line.price_subtotal = taxes_res['total_excluded']
				line.price_total = taxes_res['total_included']
			else:
				line.price_total = line.price_subtotal = subtotal
				

	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   