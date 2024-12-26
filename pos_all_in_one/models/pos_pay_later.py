# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _ , tools
from odoo.exceptions import Warning
from odoo.exceptions import RedirectWarning, UserError, ValidationError
import random
import psycopg2
import base64
from odoo.http import request
from functools import partial
from odoo.tools import float_is_zero

from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import float_is_zero, float_round, float_repr, float_compare
import logging
from collections import defaultdict
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class PosPaymentInherit(models.Model):
	_inherit = 'pos.payment'

	session_id = fields.Many2one('pos.session', related='', string='Session', store=True, index=True)

class POSConfigInherit(models.Model):
	_inherit = 'pos.config'
	
	allow_partical_payment = fields.Boolean('Allow Partial Payment')
	partial_product_id = fields.Many2one("product.product",string="Partial Payment Product", domain = [('type', '=', 'service'),('available_in_pos', '=', True)])


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'


	allow_partical_payment = fields.Boolean(related='pos_config_id.allow_partical_payment',readonly=False)
	partial_product_id = fields.Many2one(related='pos_config_id.partial_product_id',readonly=False)


	@api.model
	def create(self, vals):
		res=super(ResConfigSettings, self).create(vals)
		product=self.env['product.product'].browse(vals.get('partial_product_id',False))

		if vals.get('allow_partical_payment',False) and product:
			if product.available_in_pos != True:
				raise ValidationError(_('Please enable available in POS for the Partial Payment Product'))

			if product.taxes_id:
				raise ValidationError(_('You are not allowed to add Customer Taxes in the Partial Payment Product'))

		return res


	def write(self, vals):
		res=super(ResConfigSettings, self).write(vals)

		if self.allow_partical_payment:
			if self.partial_product_id.available_in_pos != True:
				raise ValidationError(_('Please enable available in POS for the Partial Payment Product'))

			if self.partial_product_id.taxes_id:
				raise ValidationError(_('You are not allowed to add Customer Taxes in the Partial Payment Product'))

		return res

	

class PosOrderInherit(models.Model):
	_inherit = 'pos.order'

	@api.model
	def _payment_fields(self, order, ui_paymentline):
		res = super(PosOrderInherit, self)._payment_fields(order,ui_paymentline)
		res['session_id'] = order.session_id.id

		return res

	def _default_session(self):
		return self.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)], limit=1)


	is_picking_created = fields.Boolean('Picking Created')
	is_partial = fields.Boolean('Is Partial Payment')
	amount_due = fields.Float("Amount Due",compute="get_amount_due")

	@api.depends('amount_total','amount_paid')
	def get_amount_due(self):
		for order in self :
			if order.amount_paid - order.amount_total >= 0:
				order.amount_due = 0
				order.is_partial = False
			else:
				order.amount_due = order.amount_total - order.amount_paid
				
	def write(self, vals):
		for order in self:
			if order.name == '/' and order.is_partial :
				vals['name'] = order.config_id.sequence_id._next()
		return super(PosOrderInherit, self).write(vals)

	def _is_pos_order_paid(self):
		return float_is_zero(self._get_rounded_amount(self.amount_total) - self.amount_paid, precision_rounding=self.currency_id.rounding)

	def action_pos_order_paid(self):
		self.ensure_one()
		if self.picking_ids:
			if  self._is_pos_order_paid():
				self.write({'state': 'paid'})
				return True
		else:
			if not self.is_partial:
				if not self.config_id.cash_rounding \
		   			or self.config_id.only_round_cash_method \
		   			and not any(p.payment_method_id.is_cash_count for p in self.payment_ids):
					total = self.amount_total
				else:
					total = float_round(self.amount_total, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)

				isPaid = float_is_zero(total - self.amount_paid, precision_rounding=self.currency_id.rounding)

				if not isPaid and not self.config_id.cash_rounding:
					raise UserError(_("Order %s is not fully paid.", self.name))
				elif not isPaid and self.config_id.cash_rounding:
					currency = self.currency_id
					if self.config_id.rounding_method.rounding_method == "HALF-UP":
						maxDiff = currency.round(self.config_id.rounding_method.rounding / 2)
					else:
						maxDiff = currency.round(self.config_id.rounding_method.rounding)

					diff = currency.round(self.amount_total - self.amount_paid)
					if not abs(diff) <= maxDiff:
						raise UserError(_("Order %s is not fully paid.", self.name))

				self.write({'state': 'paid'})
			if self.is_partial:
				if  self._is_pos_order_paid():
					self.write({'state': 'paid'})
					if self.picking_ids:
						return True
					else :
						return self._create_order_picking()
				else:
					if not self.picking_ids :
						return self._create_order_picking()
					else:
						return False

	@api.model
	def _order_fields(self, ui_order):
		res = super(PosOrderInherit, self)._order_fields(ui_order)
		process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
		if 'is_partial' in ui_order:
			res['is_partial'] = ui_order.get('is_partial',False) 
			res['amount_due'] = ui_order.get('amount_due',0.0) 
		return res

	@api.model
	def _process_order(self, order, draft, existing_order):
		"""Create or update an pos.order from a given dictionary.

		:param dict order: dictionary representing the order.
		:param bool draft: Indicate that the pos_order is not validated yet.
		:param existing_order: order to be updated or False.
		:type existing_order: pos.order.
		:returns: id of created/updated pos.order
		:rtype: int
		"""
		order = order['data']
		is_partial = order.get('is_partial')
		is_draft_order = order.get('is_draft_order')
		is_paying_partial = order.get('is_paying_partial')

		pos_session = self.env['pos.session'].browse(order['pos_session_id'])
		if pos_session.state == 'closing_control' or pos_session.state == 'closed':
			order['pos_session_id'] = self._get_valid_session(order).id

		pos_order = False
		if is_paying_partial:
			pos_order = self.search([('pos_reference', '=', order.get('name'))])
		else:
			if not existing_order:
				pos_order = self.create(self._order_fields(order))
			else:
				pos_order = existing_order
				pos_order.lines.unlink()
				order['user_id'] = pos_order.user_id.id
				pos_order.write(self._order_fields(order))

		if pos_order.config_id.discount_type == 'percentage':
			pos_order.update({'discount_type': "Percentage"})
			pos_order.lines.update({'discount_line_type': "Percentage"})
		if pos_order.config_id.discount_type == 'fixed':
			pos_order.update({'discount_type': "Fixed"})
			pos_order.lines.update({'discount_line_type': "Fixed"})

		pos_order = pos_order.with_company(pos_order.company_id)
		self = self.with_company(pos_order.company_id)
		self._process_payment_lines(order, pos_order, pos_session, draft)
		if not draft:
			try:
				pos_order.action_pos_order_paid()
			except psycopg2.DatabaseError:
				# do not hide transactional errors, the order(s) won't be saved!
				raise
			except Exception as e:
				_logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
		if pos_order.is_partial == False and is_paying_partial == False and  pos_order.session_id.company_id.point_of_sale_update_stock_quantities == "real": 
			pos_order._create_order_picking()
		create_invoice = False
		if order.get('to_invoice' , False) and pos_order.state == 'paid':
			if pos_order.amount_total > 0:	
				create_invoice = True
			elif pos_order.amount_total < 0:
				if pos_order.session_id.config_id.credit_note == "create_note":
					create_invoice = True
		if create_invoice:
			pos_order.action_pos_order_invoice()
			if pos_order.discount_type and pos_order.discount_type == "Fixed":
				invoice = pos_order.account_move
				for line in invoice.invoice_line_ids : 
					pos_line = line.pos_order_line_id
					if pos_line and pos_line.discount_line_type == "Fixed" and pos_line.discount != 100:
						line.write({'price_unit':pos_line.price_unit})
					else:
						line.write({'price_unit':pos_line.price_unit + line.discount,
						'discount': pos_line.discount })
					
		return pos_order.id


	def _process_payment_lines(self, pos_order, order, pos_session, draft):
		"""Create account.bank.statement.lines from the dictionary given to the parent function.

		If the payment_line is an updated version of an existing one, the existing payment_line will first be
		removed before making a new one.
		:param pos_order: dictionary representing the order.
		:type pos_order: dict.
		:param order: Order object the payment lines should belong to.
		:type order: pos.order
		:param pos_session: PoS session the order was created in.
		:type pos_session: pos.session
		:param draft: Indicate that the pos_order is not validated yet.
		:type draft: bool.
		"""
		prec_acc = order.pricelist_id.currency_id.decimal_places
		order_bank_statement_lines= self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
		is_paying_partial = pos_order.get('is_paying_partial')
		is_partial = pos_order.get('is_partial')
		if not is_paying_partial:
			order_bank_statement_lines.unlink()
		for payments in pos_order['statement_ids']:
			if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
				order.add_payment(self._payment_fields(order, payments[2]))

		order.amount_paid = sum(order.payment_ids.mapped('amount'))
		if order.amount_paid >= order.amount_total :
			order.write({
				'is_partial' : False,
			})

		if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
			cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
			if not cash_payment_method:
				raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
				
			return_amount = pos_order.get('amount_return',0)
			sc = order.pricelist_id.currency_id
			if  pos_order.get('currency_amount') and pos_order.get('currency_symbol'):
				oc = self.env['res.currency'].search([('name','=',pos_order.get('currency_name',''))])
				if oc != sc:
					return_amount = sc._convert(pos_order.get('amount_return',0), oc, order.company_id, order.date_order)

			return_payment_vals = {
				'name': _('return'),
				'pos_order_id': order.id,
                'session_id': order.session_id.id,
				'amount': -pos_order['amount_return'],
				'payment_date': fields.Datetime.now(),
				'payment_method_id': cash_payment_method.id,
				'account_currency': -return_amount or 0.0,
				'currency' : pos_order.get('currency_name',order.pricelist_id.currency_id.name),
				'is_change': True,
			}
			order.add_payment(return_payment_vals)

class PosSessionInherit(models.Model):
	_inherit = 'pos.session'

	@api.model
	def create(self, vals):
		res = super(PosSessionInherit, self).create(vals)
		orders = self.env['pos.order'].search([('user_id', '=', request.env.uid),
			('state', '=', 'draft'),('session_id.state', '=', 'closed')])
		orders.write({'session_id': res.id})
		return res

	def _check_if_no_draft_orders(self):
		draft_orders = self.order_ids.filtered(lambda order: order.state == 'draft')
		do = []
		for i in draft_orders:
			if not i.is_partial:
				do.append(i.name)
		if do:
			raise UserError(_(
				'There are still orders in draft state in the session. '
				'Pay or cancel the following orders to validate the session:\n%s'
			) % ', '.join(do)
							)
		return True

	def _create_picking_at_end_of_session(self):
		self.ensure_one()
		lines_grouped_by_dest_location = {}
		picking_type = self.config_id.picking_type_id

		if not picking_type or not picking_type.default_location_dest_id:
			session_destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
		else:
			session_destination_id = picking_type.default_location_dest_id.id

		for order in self.order_ids:
			if order.is_picking_created == False:
				if order.company_id.anglo_saxon_accounting and order.is_invoiced or order.to_ship:
					continue
				destination_id = order.partner_id.property_stock_customer.id or session_destination_id
				if destination_id in lines_grouped_by_dest_location:
					lines_grouped_by_dest_location[destination_id] |= order.lines
				else:
					lines_grouped_by_dest_location[destination_id] = order.lines

			if order.is_partial:
				order.write({
						'is_picking_created':True
					})

		for location_dest_id, lines in lines_grouped_by_dest_location.items():
			pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type)
			pickings.write({'pos_session_id': self.id, 'origin': self.name})

	def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
		bank_payment_method_diffs = bank_payment_method_diffs or {}
		for session in self:
			orders = session.order_ids.filtered(lambda order: order.is_partial == False)
			if any(order.state == 'draft' for order in orders):
				raise UserError(_("You cannot close the POS when orders are still in draft"))
			if session.state == 'closed':
				raise UserError(_('This session is already closed.'))
			session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
			if not session.config_id.cash_control:
				return session.action_pos_session_close(balancing_account, amount_to_balance, bank_payment_method_diffs)
			# If the session is in rescue, we only compute the payments in the cash register
			# It is not yet possible to close a rescue session through the front end, see `close_session_from_ui`
			if session.rescue and session.config_id.cash_control:
				default_cash_payment_method_id = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')[0]
				orders = self.order_ids.filtered(lambda o: o.state == 'paid' or o.state == 'invoiced')
				total_cash = sum(
					orders.payment_ids.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped('amount')
				) + self.cash_register_balance_start

				session.cash_register_balance_end_real = total_cash

			return session.action_pos_session_validate(balancing_account, amount_to_balance, bank_payment_method_diffs)

	def get_closing_control_data(self):
		self.ensure_one()
		order = self.order_ids.filtered(lambda o: o.state == 'paid' or o.state == 'invoiced')
		orders = order + self.order_ids.filtered(lambda o: o.is_partial == True)
		payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
		# payments = payment.filtered(lambda p: p.session_id in self.ids)
		pay_later_payments = orders.payment_ids - payments
		cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
		default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
		total_default_cash_payment_amount = sum(payments.filtered(lambda p: p.session_id.id in self.ids and p.payment_method_id == default_cash_payment_method_id).mapped('amount')) if default_cash_payment_method_id else 0
		other_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
		cash_in_count = 0
		cash_out_count = 0
		cash_in_out_list = []
		last_session = self.search([('config_id', '=', self.config_id.id), ('id', '!=', self.id)], limit=1)
		for cash_move in self.statement_line_ids.sorted('create_date'):
			if cash_move.amount > 0:
				cash_in_count += 1
				name = f'Cash in {cash_in_count}'
			else:
				cash_out_count += 1
				name = f'Cash out {cash_out_count}'
			cash_in_out_list.append({
				'name': cash_move.payment_ref if cash_move.payment_ref else name,
				'amount': cash_move.amount
			})

		final_data= {
			'orders_details': {
				'quantity': len(orders),
				'amount': sum(orders.mapped('amount_total'))
			},
			'payments_amount': sum(payments.filtered(lambda p: p.session_id.id in self.ids).mapped('amount')),
			'pay_later_amount': sum(pay_later_payments.mapped('amount')),
			'opening_notes': self.opening_notes,
			'default_cash_details': {
				'name': default_cash_payment_method_id.name,
				'amount': last_session.cash_register_balance_end_real + total_default_cash_payment_amount +
											 sum(self.statement_line_ids.mapped('amount')),
				'opening': last_session.cash_register_balance_end_real,
				'payment_amount': total_default_cash_payment_amount,
				'moves': cash_in_out_list,
				'id': default_cash_payment_method_id.id
			} if default_cash_payment_method_id else None,
			'other_payment_methods': [{
				'name': pm.name,
				'amount': sum(orders.payment_ids.filtered(lambda p: p.session_id.id in self.ids and p.payment_method_id == pm).mapped('amount')),
				'number': len(orders.payment_ids.filtered(lambda p: p.payment_method_id == pm)),
				'id': pm.id,
				'type': pm.type,
			} for pm in other_payment_method_ids],
			'is_manager': self.user_has_groups("point_of_sale.group_pos_manager"),
			'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None
		}
		return final_data

	def _cannot_close_session(self, bank_payment_method_diffs=None):
		"""
		Add check in this method if you want to return or raise an error when trying to either post cash details
		or close the session. Raising an error will always redirect the user to the back end.
		It should return {'successful': False, 'message': str, 'redirect': bool} if we can't close the session
		"""
		bank_payment_method_diffs = bank_payment_method_diffs or {}
		orders = self.order_ids.filtered(lambda order: order.is_partial == False)
		# if any(order.state == 'draft' for order in orders):
		# 	return {'successful': False, 'message': _("You cannot close the POS when orders are still in draft"), 'redirect': False}
		if self.state == 'closed':
			return {'successful': False, 'message': _("This session is already closed."), 'redirect': True}
		if bank_payment_method_diffs:
			no_loss_account = self.env['account.journal']
			no_profit_account = self.env['account.journal']
			for payment_method in self.env['pos.payment.method'].browse(bank_payment_method_diffs.keys()):
				journal = payment_method.journal_id
				compare_to_zero = self.currency_id.compare_amounts(bank_payment_method_diffs.get(payment_method.id), 0)
				if compare_to_zero == -1 and not journal.loss_account_id:
					no_loss_account |= journal
				elif compare_to_zero == 1 and not journal.profit_account_id:
					no_profit_account |= journal
			message = ''
			if no_loss_account:
				message += _("Need loss account for the following journals to post the lost amount: %s\n", ', '.join(no_loss_account.mapped('name')))
			if no_profit_account:
				message += _("Need profit account for the following journals to post the gained amount: %s", ', '.join(no_profit_account.mapped('name')))
			if message:
				return {'successful': False, 'message': message, 'redirect': False}



	def _accumulate_amounts(self, data):
		# Accumulate the amounts for each accounting lines group
		# Each dict maps `key` -> `amounts`, where `key` is the group key.
		# E.g. `combine_receivables_bank` is derived from pos.payment records
		# in the self.order_ids with group key of the `payment_method_id`
		# field of the pos.payment record.
		amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
		tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
		split_receivables_bank = defaultdict(amounts)
		split_receivables_cash = defaultdict(amounts)
		split_receivables_pay_later = defaultdict(amounts)
		combine_receivables_bank = defaultdict(amounts)
		combine_receivables_cash = defaultdict(amounts)
		combine_receivables_pay_later = defaultdict(amounts)
		combine_invoice_receivables = defaultdict(amounts)
		split_invoice_receivables = defaultdict(amounts)
		sales = defaultdict(amounts)
		taxes = defaultdict(tax_amounts)
		stock_expense = defaultdict(amounts)
		stock_return = defaultdict(amounts)
		stock_output = defaultdict(amounts)
		rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
		# Track the receivable lines of the order's invoice payment moves for reconciliation
		# These receivable lines are reconciled to the corresponding invoice receivable lines
		# of this session's move_id.
		combine_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
		split_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
		rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
		pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
		currency_rounding = self.currency_id.rounding
		order_ids = self.order_ids.filtered(lambda order: order.is_partial == False)
		for order in order_ids:
			order_is_invoiced = order.is_invoiced
			for payment in order.payment_ids:
				amount = payment.amount
				if float_is_zero(amount, precision_rounding=currency_rounding):
					continue
				date = payment.payment_date
				payment_method = payment.payment_method_id
				is_split_payment = payment.payment_method_id.split_transactions
				payment_type = payment_method.type

				# If not pay_later, we create the receivable vals for both invoiced and uninvoiced orders.
				#   Separate the split and aggregated payments.
				# Moreover, if the order is invoiced, we create the pos receivable vals that will balance the
				# pos receivable lines from the invoice payments.
				if payment_type != 'pay_later':
					if is_split_payment and payment_type == 'cash':
						split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment], {'amount': amount}, date)
					elif not is_split_payment and payment_type == 'cash':
						combine_receivables_cash[payment_method] = self._update_amounts(combine_receivables_cash[payment_method], {'amount': amount}, date)
					elif is_split_payment and payment_type == 'bank':
						split_receivables_bank[payment] = self._update_amounts(split_receivables_bank[payment], {'amount': amount}, date)
					elif not is_split_payment and payment_type == 'bank':
						combine_receivables_bank[payment_method] = self._update_amounts(combine_receivables_bank[payment_method], {'amount': amount}, date)

					# Create the vals to create the pos receivables that will balance the pos receivables from invoice payment moves.
					if order_is_invoiced:
						if is_split_payment:
							split_inv_payment_receivable_lines[payment] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
							split_invoice_receivables[payment] = self._update_amounts(split_invoice_receivables[payment], {'amount': payment.amount}, order.date_order)
						else:
							combine_inv_payment_receivable_lines[payment_method] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
							combine_invoice_receivables[payment_method] = self._update_amounts(combine_invoice_receivables[payment_method], {'amount': payment.amount}, order.date_order)

				# If pay_later, we create the receivable lines.
				#   if split, with partner
				#   Otherwise, it's aggregated (combined)
				# But only do if order is *not* invoiced because no account move is created for pay later invoice payments.
				if payment_type == 'pay_later' and not order_is_invoiced:
					if is_split_payment:
						split_receivables_pay_later[payment] = self._update_amounts(split_receivables_pay_later[payment], {'amount': amount}, date)
					elif not is_split_payment:
						combine_receivables_pay_later[payment_method] = self._update_amounts(combine_receivables_pay_later[payment_method], {'amount': amount}, date)

			if not order_is_invoiced:
				order_taxes = defaultdict(tax_amounts)
				for order_line in order.lines:
					line = self._prepare_line(order_line)
					# Combine sales/refund lines
					sale_key = (
						# account
						line['income_account_id'],
						# sign
						-1 if line['amount'] < 0 else 1,
						# for taxes
						tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
						line['base_tags'],
					)
					sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'])
					sales[sale_key].setdefault('tax_amount', 0.0)
					# Combine tax lines
					for tax in line['taxes']:
						tax_key = (tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
						sales[sale_key]['tax_amount'] += tax['amount']
						order_taxes[tax_key] = self._update_amounts(
							order_taxes[tax_key],
							{'amount': tax['amount'], 'base_amount': tax['base']},
							tax['date_order'],
							round=not rounded_globally
						)
				for tax_key, amounts in order_taxes.items():
					if rounded_globally:
						amounts = self._round_amounts(amounts)
					for amount_key, amount in amounts.items():
						taxes[tax_key][amount_key] += amount

				if self.company_id.anglo_saxon_accounting and order.picking_ids.ids:
					# Combine stock lines
					stock_moves = self.env['stock.move'].sudo().search([
						('picking_id', 'in', order.picking_ids.ids),
						('company_id.anglo_saxon_accounting', '=', True),
						('product_id.categ_id.property_valuation', '=', 'real_time')
					])
					for move in stock_moves:
						exp_key = move.product_id._get_product_accounts()['expense']
						out_key = move.product_id.categ_id.property_stock_account_output_categ_id
						amount = -sum(move.sudo().stock_valuation_layer_ids.mapped('value'))
						stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
						if move.location_id.usage == 'customer':
							stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
						else:
							stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)

				if self.config_id.cash_rounding:
					diff = order.amount_paid - order.amount_total
					rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

				# Increasing current partner's customer_rank
				partners = (order.partner_id | order.partner_id.commercial_partner_id)
				partners._increase_rank('customer_rank')

		if self.company_id.anglo_saxon_accounting:
			global_session_pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
			if global_session_pickings:
				stock_moves = self.env['stock.move'].sudo().search([
					('picking_id', 'in', global_session_pickings.ids),
					('company_id.anglo_saxon_accounting', '=', True),
					('product_id.categ_id.property_valuation', '=', 'real_time'),
				])
				for move in stock_moves:
					exp_key = move.product_id._get_product_accounts()['expense']
					out_key = move.product_id.categ_id.property_stock_account_output_categ_id
					amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
					stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
					if move.location_id.usage == 'customer':
						stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
					else:
						stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
		MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

		data.update({
			'taxes':                               taxes,
			'sales':                               sales,
			'stock_expense':                       stock_expense,
			'split_receivables_bank':              split_receivables_bank,
			'combine_receivables_bank':            combine_receivables_bank,
			'split_receivables_cash':              split_receivables_cash,
			'combine_receivables_cash':            combine_receivables_cash,
			'combine_invoice_receivables':         combine_invoice_receivables,
			'split_receivables_pay_later':         split_receivables_pay_later,
			'combine_receivables_pay_later':       combine_receivables_pay_later,
			'stock_return':                        stock_return,
			'stock_output':                        stock_output,
			'combine_inv_payment_receivable_lines': combine_inv_payment_receivable_lines,
			'rounding_difference':                 rounding_difference,
			'MoveLine':                            MoveLine,
			'split_invoice_receivables': split_invoice_receivables,
			'split_inv_payment_receivable_lines': split_inv_payment_receivable_lines,
		})
		return data


class PosMakePayment(models.TransientModel):
	_inherit = 'pos.make.payment'

	def check(self):
		"""Check the order:
		if the order is not paid: continue payment,
		if the order is paid print ticket.
		"""
		self.ensure_one()
		order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
		if self.payment_method_id.split_transactions and not order.partner_id:
			raise UserError(_(
				"Customer is required for %s payment method.",
				self.payment_method_id.name
			))
		currency = order.currency_id

		init_data = self.read()[0]
		if not float_is_zero(init_data['amount'], precision_rounding=currency.rounding):
			order.add_payment({
				'pos_order_id': order.id,
				'session_id' : order.session_id.id,
				'amount': order._get_rounded_amount(init_data['amount']),
				'name': init_data['payment_name'],
				'payment_method_id': init_data['payment_method_id'][0],
			})

		"""
			Refund Functionality
		"""
		if order.refunded_order_ids:
			for r_line in order.lines:
				po_line_obj = self.env['pos.order.line']
				rm_line = po_line_obj.browse(r_line.id)	
				for m_order in order.refunded_order_ids : 
					main_order=self.env['pos.order'].browse(m_order.id)
					po_line_obj = self.env['pos.order.line']
					for l in main_order.lines:
						line = po_line_obj.browse(l.id)
						if line:
							line.write({
								'return_qty' : line.return_qty - rm_line.qty,
							})	

		if order.is_partial == True:
			if order._is_pos_order_paid():
				order.action_pos_order_paid()
				order._compute_total_cost_in_real_time()
				return {'type': 'ir.actions.act_window_close'}
		else:
			if order._is_pos_order_paid():
				order.action_pos_order_paid()
				order._create_order_picking()
				order._compute_total_cost_in_real_time()
				return {'type': 'ir.actions.act_window_close'}
		return self.launch_payment()