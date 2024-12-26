# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _
import datetime
from odoo.exceptions import ValidationError, UserError, AccessError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    carry_forward_paid = fields.Float("Paid from Carry Forward", copy=False)
    linked_bill_ids = fields.Many2many('account.move', 'rel_bill_payment', 'invoice_id', 'payment_id',
                                       string='Linked Bills', copy=False, readonly=False)

    @api.model
    def default_get(self, default_fields):
        values = super(AccountPayment, self).default_get(default_fields)
        discount_account_id = self.env.company.invoice_discount_account_id.id
        writeoff_account_id = self.env.company.invoice_writeoff_account_id.id
        sale_tax_account_id = self.env.company.invoice_sale_tax_account_id.id
        values.update({
            'discount_account_id': discount_account_id,
            'writeoff_account_id': writeoff_account_id,
            'sale_tax_account_id': sale_tax_account_id,
        })

        # if 'active_model' in self._context and self._context.get('active_model') == 'account.payment':
        #     values.update({
        #         'payment_allocation': True
        #     })
        #
        # elif 'params' in self._context and self._context.get('params')['model'] == 'account.payment':
        #     values.update({
        #         'payment_allocation': True
        #     })
        return values

    invoice_lines = fields.One2many('payment.invoice.line', 'payment_id',
                                    string="Invoice Line", copy=False)

    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        currency_field='currency_id',
        compute='_get_remaining_amount',
        store=True,
        help="This will show remaining amount that can be allocated to invoices/bills")

    total_amount = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        compute='_get_remaining_amount',
        help="This will show sum of current payment amount + outstanding"
             " utilization",
        store=True)
    select_all = fields.Boolean(string="Select ALL", copy=False)
    check_all_posted = fields.Boolean(string="Check All Posted",
                                      compute='_compute_check_all_posted',
                                      store=True)
    outstanding_payment_ids = fields.One2many('outstanding.payment.line',
                                              'payment_id',
                                              string="Outstanding Payments", copy=False)
    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_discount_amount',
        currency_field='currency_id',
        store=True,
        help="This will show sum of all discount amount of invoices/bills")
    sale_tax = fields.Monetary(
        string='Sale Tax Amount',
        compute='_compute_sale_tax_amount',
        currency_field='currency_id',
        store=True,
        help="This will show sum of all sale tax amount of invoices/bills")
    writeoff_amount = fields.Monetary(
        string='Write-Off Amount',
        compute='_compute_writeoff_amount',
        currency_field='currency_id',
        store=True,
        help="This will show sum of all payment difference amount of invoices which is marked as paid.")
    discount_account_id = fields.Many2one('account.account',
                                          string="Discount Account")
    writeoff_account_id = fields.Many2one('account.account',
                                          string="Write-Off Account")
    sale_tax_account_id = fields.Many2one('account.account',
                                          string="Sale Tax Account")
    created_from_register_payment = fields.Boolean(
        string="Created From Register Payment", copy=False)
    is_hide_allocation = fields.Boolean(string="Hide Allocation", compute='_compute_hide_allocation')
    is_utilize = fields.Boolean(string="Is Utilize",
                                help="If enabled it will utilize all credits and outstanding amount of invoices/bills.")

    payment_outstanding_amount = fields.Monetary(string="Outstanding Amount", compute='_compute_outstanding_amount',
                                                 store=True, compute_sudo=True)
    carry_forward_move_ids = fields.Many2many('account.move', 'rel_carry_forward_move_payment',
                                              'payment_id', 'move_id',
                                              string='Carry Forward Moves', copy=False)
    payment_allocation = fields.Boolean(string="Payment Allocation", copy=False)
    carry_forward_count = fields.Integer(compute="_compute_carry_forward_bool_move", default=0, copy=False)

    @api.depends('move_id.line_ids.amount_residual')
    def _compute_outstanding_amount(self):
        for rec in self:
            if rec.move_id and rec.state not in ('draft', 'cancel'):
                payment_outstanding_amount = abs(sum(rec.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')).mapped(
                    'amount_residual')))

                carry_forward_move_ar_ap_id = rec.carry_forward_move_ids.filtered(
                    lambda m: m.state == 'posted').line_ids.filtered(
                    lambda l: l.account_id.account_type in (
                        'asset_receivable', 'liability_payable') and l.move_id.related_payment_id)
                payment_outstanding_amount += abs(sum(carry_forward_move_ar_ap_id.mapped('amount_residual')))
                rec.payment_outstanding_amount = payment_outstanding_amount
            else:
                rec.payment_outstanding_amount = 0.0

    @api.onchange('date')
    def _onchange_date(self):
        """update allowed discount amount based on payment date"""
        for invoice_line in self.invoice_lines:
            if invoice_line.invoice_id.state == 'posted':
                # check for allowed discount
                main_ml_id = invoice_line.move_line_ids[:1]
                # if len(invoice_line.move_line_ids) > 1:
                #     if invoice_line.payment_id.date and main_ml_id.date_maturity > self.date:
                #         discount_ml_ids = invoice_line.move_line_ids[1:]
                #         invoice_line.amount_allowed_discount = sum(discount_ml_ids.mapped('amount_residual'))


                if invoice_line.invoice_id.invoice_payment_term_id:
                    discount_percentage = 0.0
                    discount_days = 0
                    for invoice_payment_line_id in invoice_line.invoice_id.invoice_payment_term_id.line_ids:
                        if invoice_payment_line_id.discount_percentage > 0.0:
                            discount_percentage = invoice_payment_line_id.discount_percentage
                            discount_days = invoice_payment_line_id.discount_days
                            break

                    if discount_percentage > 0.0 and discount_days == 0:
                        if invoice_line.invoice_id.invoice_date == self.date:
                            invoice_line.amount_allowed_discount = (invoice_line.invoice_id.amount_residual / 100) * discount_percentage
                    if discount_percentage > 0.0 and discount_days > 0:
                        discount_days = invoice_line.invoice_id.invoice_date + datetime.timedelta(discount_days)
                        if self.date >= invoice_line.invoice_id.invoice_date and self.date <= discount_days:
                            invoice_line.amount_allowed_discount = (invoice_line.invoice_id.amount_residual / 100) * discount_percentage

    def clear_selection(self, active_id=None):
        if active_id:
            self = self.env['account.payment'].browse(active_id)
        try:
            # has_group = self.env.user.has_group('account.group_account_manager')
            has_group = self.env.user.has_group('account.group_account_invoice')
            if not has_group and not self._context.get('allow_access'):
                raise UserError(
                    _("You do not have access to perform this action."))

            if self.is_hide_allocation and not self._context.get('allow_access'):
                raise UserError(
                    "You can not modify allocation when payment is reconciled with any invoice/bill.")

            self.deselect_all_invoce()
            self.invoice_lines.write({'select': False})
            for line in self.invoice_lines:
                line.onchange_select()
            if self._context.get('allow_access'):
                self.with_context(force_edit_move=True)._synchronize_to_moves(changed_fields=set({}))

        except Exception as error:
            return error

    @api.onchange('is_utilize')
    def _onchange_is_utilize(self):
        """here we first utilise all credits and then outstanding amount until all invoice will be paid"""
        if not self.is_utilize:
            self.outstanding_payment_ids.update({'amount_to_utilize': 0.0})
            return

        total_invoice_amount = abs(sum(self.invoice_lines.mapped('open_amount')))

        for rec in self.outstanding_payment_ids.filtered(lambda o: o.move_id):
            if abs(rec.amount_residual) < total_invoice_amount:
                rec.amount_to_utilize = rec.amount_residual
                total_invoice_amount -= abs(rec.amount_residual)
            elif abs(rec.amount_residual) > total_invoice_amount:
                rec.amount_to_utilize = total_invoice_amount
                total_invoice_amount -= abs(rec.amount_residual)
                use_payment = False
                break

        for rec in self.outstanding_payment_ids.filtered(lambda o: o.move_payment_id):
            if abs(rec.amount_residual) < total_invoice_amount:
                rec.amount_to_utilize = rec.amount_residual
                total_invoice_amount -= abs(rec.amount_residual)
            elif abs(rec.amount_residual) > total_invoice_amount:
                rec.amount_to_utilize = total_invoice_amount
                total_invoice_amount -= abs(rec.amount_residual)
                break
        for out_line in self.outstanding_payment_ids:
            out_line.onchange_amount_to_utilize()

    def _compute_hide_allocation(self):
        for rec in self:
            if rec.check_all_posted:
                rec.is_hide_allocation = True
            elif rec.total_amount != 0.0 and rec.amount == 0.0 and rec.check_all_posted and rec.is_reconciled:
                rec.is_hide_allocation = True
            elif rec.state == 'cancel':
                rec.is_hide_allocation = True
            elif rec.reconciled_bill_ids or rec.reconciled_invoice_ids:
                rec.is_hide_allocation = True
            else:
                rec.is_hide_allocation = False

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.outstanding_payment_ids or self.invoice_lines:
            self.invoice_lines = False
            self.outstanding_payment_ids = False
            warnings = {
                'title': _('Warning!'),
                'message': 'Payment Type Changed! \nYou need to update invoice again, '
                           'or discard changes.'}
            return {'warning': warnings}

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.outstanding_payment_ids or self.invoice_lines:
            self.invoice_lines = False
            self.outstanding_payment_ids = False
            warnings = {
                'title': _('Warning!'),
                'message': 'Partner Changed! \nYou need to update invoice again, '
                           'or discard changes.'}
            return {'warning': warnings}

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        if self.outstanding_payment_ids or self.invoice_lines:
            self.invoice_lines = False
            self.outstanding_payment_ids = False
            warnings = {
                'title': _('Warning!'),
                'message': 'Partner Type Changed! \nYou need to update invoice again, '
                           'or discard changes.'}
            return {'warning': warnings}

    @api.depends('invoice_lines.discount_amount')
    def _compute_discount_amount(self):
        for rec in self:
            rec.discount_amount = abs(
                sum(rec.invoice_lines.mapped('discount_amount')))

    @api.depends('invoice_lines.sale_tax')
    def _compute_sale_tax_amount(self):
        for rec in self:
            rec.sale_tax = abs(sum(rec.invoice_lines.mapped('sale_tax')))

    @api.depends('invoice_lines.payment_difference',
                 'invoice_lines.select_all')
    def _compute_writeoff_amount(self):
        for rec in self:
            rec.writeoff_amount = abs(sum(rec.invoice_lines.filtered(
                lambda l: l.payment_difference != 0.0 and l.select_all).mapped(
                'payment_difference')))

    def add_previous_outstanding_payment(self):
        # self.outstanding_payment_ids = False
        outstanding_payment_ids = self.outstanding_payment_ids.filtered(
            lambda p: p.move_payment_id).mapped('move_payment_id')
        if self.partner_type == 'customer':
            domain = [('partner_id', '=', self.commercial_partner_id.id),
                      ('reconciled', '=', False),
                      ('amount_residual', '!=', 0.0),
                      ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                      ('company_id', '=', self.company_id.id),
                      ('move_id.payment_id', '!=', False),
                      ('move_id.payment_id', 'not in',
                       outstanding_payment_ids.ids + [self.id]),
                      ('move_id.payment_id.payment_type', '=',
                       self.payment_type),
                      ('move_id.payment_id.partner_type', '=', 'customer'),
                      ('move_id.state', '=', 'posted'),
                      ]
            if self.currency_id:
                domain.append(('currency_id', '=', self.currency_id.id))
        if self.partner_type == 'supplier':
            domain = [('partner_id', '=', self.commercial_partner_id.id),
                      ('reconciled', '=', False),
                      ('amount_residual', '!=', 0.0),
                      ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                      ('company_id', '=', self.company_id.id),
                      ('move_id.payment_id', '!=', False),
                      ('move_id.payment_id', 'not in',
                       outstanding_payment_ids.ids + [self.id]),
                      ('move_id.payment_id', '!=', self.id),
                      ('move_id.payment_id.payment_type', '=',
                       self.payment_type),
                      ('move_id.payment_id.partner_type', '=', 'supplier'),
                      ('move_id.state', '=', 'posted'),
                      ]
            if self.currency_id:
                domain.append(('currency_id', '=', self.currency_id.id))

        outstanding_payments = self.env['account.move.line'].search(domain)
        if self.payment_type == 'outbound':
            move_line_id = self.env['account.move.line'].search([
                ('payment_id', '=', self.id), ('debit', '!=', '0.0'),
                ('move_id.payment_id', 'not in',
                 outstanding_payment_ids.ids)], limit=1)
            outstanding_payments += move_line_id
        if self.payment_type == 'inbound':
            move_line_id = self.env['account.move.line'].search([
                ('payment_id', '=', self.id), ('credit', '!=', '0.0'),
                ('move_id.payment_id', 'not in',
                 outstanding_payment_ids.ids)], limit=1)
            outstanding_payments += move_line_id

        line_list = []
        for line in outstanding_payments:
            allocation = 0
            if line.payment_id.id == self.id:
                allocation = line.amount_residual
            line_list.append((0, 0, {
                'reference': line.move_id.payment_id.name,
                'move_line_id': line.id,
                'amount_residual': line.amount_residual,
                'amount_to_utilize': allocation,
                'currency_id': line.currency_id.id,
                'move_payment_id': line.move_id.payment_id.id,
                'payment_date': line.move_id.payment_id.date,
                'is_current_payment': True if line.move_id.payment_id.id == self.id else False,
            }))

        # logic for carry forward moves to use as outstanding payment
        if self.partner_type == 'customer':
            domain = [('partner_id', '=', self.commercial_partner_id.id),
                      ('reconciled', '=', False),
                      ('amount_residual', '!=', 0.0),
                      ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                      ('company_id', '=', self.company_id.id),
                      ('move_id.related_payment_id', '!=', False),
                      ('move_id.related_payment_id', 'not in',
                       outstanding_payment_ids.ids + [self.id]),
                      ('move_id.related_payment_id.payment_type', '=',
                       self.payment_type),
                      ('move_id.related_payment_id.partner_type', '=', 'customer'),
                      ('move_id.state', '=', 'posted'),
                      ]
            if self.currency_id:
                domain.append(('currency_id', '=', self.currency_id.id))
        if self.partner_type == 'supplier':
            domain = [('partner_id', '=', self.commercial_partner_id.id),
                      ('reconciled', '=', False),
                      ('amount_residual', '!=', 0.0),
                      ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                      ('company_id', '=', self.company_id.id),
                      ('move_id.related_payment_id', '!=', False),
                      ('move_id.related_payment_id', 'not in',
                       outstanding_payment_ids.ids + [self.id]),
                      ('move_id.related_payment_id', '!=', self.id),
                      ('move_id.related_payment_id.payment_type', '=',
                       self.payment_type),
                      ('move_id.related_payment_id.partner_type', '=', 'supplier'),
                      ('move_id.state', '=', 'posted'),
                      ]
            if self.currency_id:
                domain.append(('currency_id', '=', self.currency_id.id))

        outstanding_payments = self.env['account.move.line'].search(domain)

        for line in outstanding_payments:
            allocation = 0
            if line.payment_id.id == self.id:
                allocation = line.amount_residual
            line_list.append((0, 0, {
                'reference': line.move_id.name,
                'move_id': line.move_id.id,
                'move_line_id': line.id,
                'amount_residual': line.amount_residual,
                'amount_to_utilize': 0,
                'currency_id': line.currency_id.id,
                'move_payment_id': False,
                'payment_date': line.date_maturity,
            }))

        self.outstanding_payment_ids = line_list

    @api.depends('invoice_lines.state', 'created_from_register_payment')
    def _compute_check_all_posted(self):
        for rec in self:
            if rec.created_from_register_payment:
                rec.check_all_posted = True
            elif rec.invoice_lines and all(
                    inv.state == 'posted' for inv in rec.invoice_lines):
                rec.check_all_posted = True
            else:
                rec.check_all_posted = False

    def action_draft(self):
        if self.reconciled_statement_lines_count > 0:
            raise ValidationError(_("First you should unlink this payment from the statement."))
        res = super(AccountPayment, self.with_context(allow_draft=True)).action_draft()
        for rec in self:
            # unlink all partial reconcile of utilized outstanding payment
            # which is created from this payment
            partial_ids = self.env['account.partial.reconcile'].search(
                [('payment_id', '=', self.id)])
            partial_ids.unlink()
            rec.created_from_register_payment = False
            rec.invoice_lines.write({'state': 'draft'})
            common_ids = self.env['common.allocation'].search([('linked_payment_id', '=', self.id)])
            if common_ids:
                common_ids.unlink()
            rec.with_context(allow_access=True).clear_selection()
        # writeoff_line_id = self.move_id.line_ids.filtered(lambda l: l.is_extra_line == True)
        # writeoff_line_id.unlink()

        # prevent delete if carry forward move is used
        carry_forward_move_ar_ap_id = self.carry_forward_move_ids.filtered(
            lambda m: m.state == 'posted').line_ids.filtered(lambda l: l.account_id.account_type in (
        'asset_receivable', 'liability_payable') and l.move_id.related_payment_id)
        if carry_forward_move_ar_ap_id and carry_forward_move_ar_ap_id.credit > 0.0 and abs(
                carry_forward_move_ar_ap_id.credit) != abs(carry_forward_move_ar_ap_id.amount_residual):
            raise UserError("You can not delete this payment as it is used to carry forward outstanding amount.")
        if carry_forward_move_ar_ap_id and carry_forward_move_ar_ap_id.debit > 0.0 and abs(
                carry_forward_move_ar_ap_id.debit) != abs(carry_forward_move_ar_ap_id.amount_residual):
            raise UserError("You can not delete this payment as it is used to carry forward outstanding amount.")

        carry_move_id = self.carry_forward_move_ids.filtered(lambda m: m.state == 'posted')
        carry_move_id.with_context(allow_draft=True).button_draft()
        carry_move_id.button_cancel()
        return res

    @api.depends('invoice_lines.allocation',
                 'outstanding_payment_ids.amount_to_utilize', 'amount')
    def _get_remaining_amount(self):
        for rec in self:
            outstanding_payment = abs(
                sum(rec.outstanding_payment_ids.mapped('amount_to_utilize')))
            rec.remaining_amount = outstanding_payment
            total_amount = outstanding_payment

            # consider refund/credit note allocation to add it in remaining
            # amount
            total_allocation = abs(sum(rec.invoice_lines.mapped(
                'allocation')))
            # if rec.payment_type == 'outbound' and rec.partner_type == 'supplier':
            #     total_allocation = abs(sum(rec.invoice_lines.filtered(
            #         lambda m: m.invoice_id.move_type == 'in_invoice').mapped(
            #         'allocation')))
            # elif rec.payment_type == 'inbound' and rec.partner_type == 'supplier':
            #     total_allocation = abs(sum(rec.invoice_lines.filtered(
            #         lambda m: m.invoice_id.move_type == 'in_refund').mapped(
            #         'allocation')))
            # elif rec.payment_type == 'inbound' and rec.partner_type == 'customer':
            #     total_allocation = abs(sum(rec.invoice_lines.filtered(
            #         lambda m: m.invoice_id.move_type == 'out_invoice').mapped(
            #         'allocation')))
            # elif rec.payment_type == 'outbound' and rec.partner_type == 'customer':
            #     total_allocation = abs(sum(rec.invoice_lines.filtered(
            #         lambda m: m.invoice_id.move_type == 'out_refund').mapped(
            #         'allocation')))

            rec.total_amount = total_amount

            rec.remaining_amount = total_amount - total_allocation

    def update_invoice_lines(self):
        if self.reconciled_bill_ids or self.reconciled_invoice_ids:
            raise UserError(
                "There is already some moves reconciled with this payment. \nCan not use payment allocation feature here.")
        for invoice_line in self.invoice_lines:
            if invoice_line.invoice_id.state == 'posted' and invoice_line.invoice_id.move_type in (
                    'out_invoice', 'in_refund', 'out_refund', 'in_invoice'):
                invoice_line.open_amount = sum(invoice_line.move_line_ids.mapped('amount_residual'))
            else:
                invoice_line.open_amount = 0
            invoice_line._get_currency_amount()

        self.prepare_invoice_lines()
        self.add_previous_outstanding_payment()

    def allocate_to_vendor_bill_send_money(self):
        remaining_payment_amount = self.remaining_amount
        bill_move_ids = self.invoice_lines.filtered(
            lambda m: m.invoice_id.move_type == 'in_invoice')
        if any(line.select for line in bill_move_ids):
            bill_move_ids = bill_move_ids.filtered(lambda m: m.select)

        for pay_line in bill_move_ids:
            if pay_line.allocation != 0.0:
                continue
            allocation_amount = abs(pay_line.open_amount) - \
                                abs(pay_line.discount_amount) - \
                                abs(pay_line.sale_tax)
            if abs(allocation_amount) < abs(remaining_payment_amount):
                # pay_line.update({'select_all': True})

                pay_line._onchange_select_all(select_all=True)
                remaining_payment_amount -= allocation_amount
            else:
                select_all = False
                if round(abs(remaining_payment_amount), 2) == round(
                        abs(allocation_amount), 2):
                    select_all = True
                pay_line.update({'allocation': remaining_payment_amount * -1,
                                 'select_all': select_all})
                break
        self.select_all = True

    def allocate_to_vendor_bill_receive_money(self):
        remaining_payment_amount = self.remaining_amount
        refund_move_ids = self.invoice_lines.filtered(
            lambda m: m.invoice_id.move_type == 'in_refund')
        if any(line.select for line in refund_move_ids):
            refund_move_ids = refund_move_ids.filtered(lambda m: m.select)

        for pay_line in refund_move_ids:
            if pay_line.allocation != 0:
                continue
            allocation_amount = pay_line.open_amount - \
                                pay_line.discount_amount - pay_line.sale_tax
            if abs(allocation_amount) < abs(remaining_payment_amount):
                pay_line._onchange_select_all(select_all=True)
                remaining_payment_amount -= allocation_amount
            else:
                select_all = False
                if round(abs(remaining_payment_amount), 2) == round(
                        abs(allocation_amount), 2):
                    select_all = True
                pay_line.update({'allocation': remaining_payment_amount,
                                 'select_all': select_all})
                break
        self.select_all = True

    def allocate_to_customer_invoice_receive_money(self):
        remaining_payment_amount = self.remaining_amount
        bill_move_ids = self.invoice_lines.filtered(
            lambda m: m.invoice_id.move_type == 'out_invoice')
        if any(line.select for line in bill_move_ids):
            bill_move_ids = bill_move_ids.filtered(lambda m: m.select)

        for pay_line in bill_move_ids:
            if pay_line.allocation != 0:
                continue
            allocation_amount = pay_line.open_amount - \
                                pay_line.discount_amount - pay_line.sale_tax
            if round(abs(allocation_amount), 2) < round(
                    abs(remaining_payment_amount), 2):
                pay_line._onchange_select_all(select_all=True)
                remaining_payment_amount -= allocation_amount
            else:
                select_all = False
                if round(abs(remaining_payment_amount), 2) == round(
                        abs(allocation_amount), 2):
                    select_all = True
                pay_line.update({'allocation': remaining_payment_amount,
                                 'select_all': select_all})
                break
        self.select_all = True

    def allocate_to_customer_invoice_send_money(self):
        remaining_payment_amount = self.remaining_amount
        refund_move_ids = self.invoice_lines.filtered(
            lambda m: m.invoice_id.move_type == 'out_refund')
        if any(line.select for line in refund_move_ids):
            refund_move_ids = refund_move_ids.filtered(lambda m: m.select)

        for pay_line in refund_move_ids:
            if pay_line.allocation != 0:
                continue
            allocation_amount = abs(pay_line.open_amount) - \
                                abs(pay_line.discount_amount) - \
                                abs(pay_line.sale_tax)
            if abs(allocation_amount) < abs(remaining_payment_amount):
                pay_line._onchange_select_all(select_all=True)
                remaining_payment_amount -= allocation_amount
            else:
                select_all = False
                if round(abs(remaining_payment_amount), 2) == round(
                        abs(allocation_amount), 2):
                    select_all = True
                pay_line.update({'allocation': remaining_payment_amount * -1,
                                 'select_all': select_all})
                break
        self.select_all = True

    def select_all_invoice(self, active_id=None):
        """allocate amount to all invoices/credit notes or vendor bills/ refunds"""

        if active_id:
            self = self.env['account.payment'].browse(active_id)

        # has_group = self.env.user.has_group('account.group_account_manager')
        has_group = self.env.user.has_group('account.group_account_invoice')
        if not has_group:
            raise UserError(
                _("You do not have access to perform this action."))

        if self.is_hide_allocation:
            raise UserError(
                "You can not modify allocation when payment is reconciled with any invoice/bill.")

        self.ensure_one()
        if not self.invoice_lines:
            raise UserError("No invoice found for allocation!")
        if not self.remaining_amount:
            raise UserError("No remaining amount to allocate!")
        if any(line.select for line in self.invoice_lines):
            # add validation if credit/refund is selected more then
            # bill/invoice and vice versa
            if self.payment_type == 'inbound' and self.partner_type == 'customer':
                total_credit_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'out_refund' and m.select).mapped(
                    'open_amount')
                total_invoice_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'out_invoice' and m.select).mapped(
                    'open_amount')
                if abs(sum(total_credit_due)) > abs(sum(total_invoice_due)):
                    raise ValidationError(
                        _("You can not select more amount credit notes than invoices. when payment type is Receive Money for customer."))

            elif self.payment_type == 'inbound' and self.partner_type == 'supplier':
                total_credit_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'in_refund' and m.select).mapped(
                    'open_amount')
                total_invoice_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'in_invoice' and m.select).mapped(
                    'open_amount')
                if abs(sum(total_invoice_due)) > abs(sum(total_credit_due)):
                    raise ValidationError(
                        _("You can not select more bills than refund. when payment type is Receive Money for vendor."))

            elif self.payment_type == 'outbound' and self.partner_type == 'customer':
                total_credit_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'out_refund' and m.select).mapped(
                    'open_amount')
                total_invoice_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'out_invoice' and m.select).mapped(
                    'open_amount')
                if abs(sum(total_invoice_due)) > abs(sum(total_credit_due)):
                    raise ValidationError(
                        _("You can not select more invoices than credit notes. when payment type is Send Money for customer."))

            elif self.payment_type == 'outbound' and self.partner_type == 'supplier':
                total_credit_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'in_refund' and m.select).mapped(
                    'open_amount')
                total_invoice_due = self.invoice_lines.filtered(
                    lambda
                        m: m.invoice_id.move_type == 'in_invoice' and m.select).mapped(
                    'open_amount')

                if abs(sum(total_credit_due)) > abs(sum(total_invoice_due)):
                    raise ValidationError(
                        _("You can not select more refunds than bills. when payment type is Send Money for vendor."))

        if self.payment_type == 'outbound' and self.partner_type == 'supplier':
            self.allocate_to_vendor_bill_send_money()
        elif self.payment_type == 'inbound' and self.partner_type == 'supplier':
            self.allocate_to_vendor_bill_receive_money()
        elif self.payment_type == 'inbound' and self.partner_type == 'customer':
            self.allocate_to_customer_invoice_receive_money()
        elif self.payment_type == 'outbound' and self.partner_type == 'customer':
            self.allocate_to_customer_invoice_send_money()

    def deselect_all_invoce(self, active_id=None):
        if active_id:
            self = self.env['account.payment'].browse(active_id)
        try:
            # has_group = self.env.user.has_group('account.group_account_manager')
            has_group = self.env.user.has_group('account.group_account_invoice')
            if not has_group and not self._context.get('allow_access'):
                raise UserError(
                    _("You do not have access to perform this action."))

            if self.is_hide_allocation and not self._context.get('allow_access'):
                raise UserError(
                    "You can not modify allocation when payment is reconciled with any invoice/bill.")
            self.ensure_one()
            self.select_all = False

            # update amount_to_utilize to zero
            for outstanding_id in self.outstanding_payment_ids:
                if self.name != outstanding_id.display_name:
                    outstanding_id.amount_to_utilize = 0.0
                    outstanding_id.common_allocation_id.select = False
                else:
                    outstanding_id.is_current_payment = True

            if self.invoice_lines:
                self.select_all = False
                for line in self.invoice_lines:
                    line.update({'select_all': False, 'allocation': 0.0})
                    line.onchange_make_select_all()
                # added to remove writeoff JE line when deselect all
                # self.with_context(force_edit_move=True)._synchronize_to_moves(
                #     changed_fields=set({}))
        except Exception as error:
            return error

    def allocate_discount_amount(self, active_id=None):
        if active_id:
            self = self.env['account.payment'].browse(active_id)
        try:
            # has_group = self.env.user.has_group('account.group_account_manager')
            has_group = self.env.user.has_group('account.group_account_invoice')
            if not has_group and not self._context.get('allow_access'):
                raise UserError(
                    _("You do not have access to perform this action."))

            if self.is_hide_allocation and not self._context.get('allow_access'):
                raise UserError(
                    "You can not modify allocation when payment is reconciled with any invoice/bill.")
            self.ensure_one()
            if self.invoice_lines:
                for line in self.invoice_lines:
                    if line.amount_allowed_discount > 0:
                        line.discount_amount = line.amount_allowed_discount
        except Exception as error:
            return error

    def _create_invoice_lines(self, debit_move_ids, credit_move_lines):
        line = []

        for move_id in debit_move_ids:
            # find AP/AR move lines with residual amount
            move_line_ids = move_id.line_ids.filtered(
                lambda m: m.account_id.account_type in ['asset_receivable',
                                                        'liability_payable'] and m.amount_residual != 0.0)
            residual_amount = sum(move_line_ids.mapped('amount_residual'))

            today = self.date
            date_maturity = False
            for move_line in move_line_ids:
                if move_line.date_maturity and move_line.date_maturity >= today:
                    date_maturity = move_line.date_maturity
                    break
            if not date_maturity:
                date_maturity = move_line_ids[-1:].date_maturity
            if residual_amount != 0.0:
                vals = {
                    'invoice_id': move_id.id,
                    'date': move_id.invoice_date,
                    # 'move_line_id': move_line.id,
                    'payment_date': date_maturity,
                    'open_amount': residual_amount,
                    'move_line_ids': [(6, 0, move_line_ids.ids)]
                }
                line.append((0, 0, vals))
        self.invoice_lines = line

        # add credit line in outstanding
        line_list = []
        for move_line in credit_move_lines:
            line_list.append((0, 0, {
                'reference': move_line.move_id.name,
                'move_id': move_line.move_id.id,
                'move_line_id': move_line.id,
                'amount_residual': move_line.amount_residual,
                'amount_to_utilize': 0,
                'currency_id': move_line.currency_id.id,
                'move_payment_id': False,
                'payment_date': move_line.date_maturity,
            }))

        self.outstanding_payment_ids = line_list
        self.update_amounts()
        # self._change_payment_type()

    def prepare_invoice_lines(self):
        if not self.partner_id:
            self.invoice_lines = False

        if self.invoice_lines:
            zero_invoice_lines = self.invoice_lines.filtered(
                lambda
                    il: il.allocation == 0.0 and il.discount_amount == 0.0 and il.sale_tax == 0.0 and not il.select)
            self.invoice_lines = [(3, zero_invoice_lines.ids)]

        if self.outstanding_payment_ids:
            zero_outstanding_lines = self.outstanding_payment_ids.filtered(
                lambda ol: ol.amount_to_utilize == 0.0)
            self.outstanding_payment_ids = [(3, zero_outstanding_lines.ids)]

        move_types = self.invoice_lines.mapped(
            'invoice_id').mapped('move_type')
        if self.payment_type == 'inbound':
            if 'in_invoice' in move_types or 'out_refund' in move_types:
                self.invoice_lines = False
        if self.payment_type == 'outbound':
            if 'out_invoice' in move_types or 'in_refund' in move_types:
                self.invoice_lines = False

        if self.partner_id and self.partner_type == 'customer':
            # for customer invoice and credit note
            credit_move_type = self._get_credit_invoice_type_for_outstanding()
            debit_move_type = 'out_refund'
            if credit_move_type == 'out_refund':
                debit_move_type = 'out_invoice'
            search_domain = [
                ('company_id', '=', self.company_id.id),
                ('commercial_partner_id', '=', self.commercial_partner_id.id),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0),
            ]
            debit_domain = search_domain + [('move_type',
                                             '=',
                                             debit_move_type),
                                            ('id',
                                             'not in',
                                             self.invoice_lines.mapped(
                                                 'invoice_id').ids)]
            debit_move_ids = self.env['account.move'].search(debit_domain)

            # debit_move_lines = self.env['account.move.line'].search(
            #     [('move_id', 'in', debit_move_ids.ids),
            #      ('account_id', '=',
            #       self.partner_id.property_account_receivable_id.id)])

            # credit moves
            credit_outstanding_ids = self.outstanding_payment_ids.mapped(
                'move_id').ids
            credit_domain = search_domain + [
                ('move_type', '=', credit_move_type),
                ('id', 'not in', credit_outstanding_ids)]
            credit_move_ids = self.env['account.move'].search(credit_domain)

            credit_move_lines = self.env['account.move.line'].search(
                [('move_id', 'in', credit_move_ids.ids),
                 ('account_id', '=',
                  self.partner_id.property_account_receivable_id.id)
                    , ('is_extra_line', '=', False)])
            self._create_invoice_lines(debit_move_ids, credit_move_lines)

        elif self.partner_id and self.partner_type == 'supplier':
            # for vendor bill and credit note
            credit_move_type = self._get_credit_invoice_type_for_outstanding()
            debit_move_type = 'in_refund'
            if credit_move_type == 'in_refund':
                debit_move_type = 'in_invoice'

            search_domain = [
                ('company_id', '=', self.company_id.id),
                ('commercial_partner_id', '=', self.commercial_partner_id.id),
                ('state', '=', 'posted'),
                ('amount_residual', '>', 0),
            ]
            debit_domain = search_domain + [('move_type',
                                             '=',
                                             debit_move_type),
                                            ('id',
                                             'not in',
                                             self.invoice_lines.mapped(
                                                 'invoice_id').ids)]
            debit_move_ids = self.env['account.move'].search(debit_domain)

            # debit_move_lines = self.env['account.move.line'].search(
            #     [('move_id', 'in', debit_move_ids.ids),
            #      ('account_id', '=',
            #       self.partner_id.property_account_payable_id.id)])

            # credit moves
            credit_outstanding_ids = self.outstanding_payment_ids.mapped(
                'move_id').ids
            credit_domain = search_domain + [
                ('move_type', '=', credit_move_type),
                ('id', 'not in', credit_outstanding_ids),
            ]
            credit_move_ids = self.env['account.move'].search(credit_domain)

            credit_move_lines = self.env['account.move.line'].search(
                [('move_id', 'in', credit_move_ids.ids),
                 ('account_id', '=',
                  self.partner_id.property_account_payable_id.id)
                    , ('is_extra_line', '=', False)
                 ])
            self._create_invoice_lines(debit_move_ids, credit_move_lines)

    def _get_credit_invoice_type_for_outstanding(self):
        for rec in self:
            if rec.payment_id.payment_type == 'inbound' and rec.payment_id.partner_type == 'customer':
                return 'out_refund'
            elif rec.payment_id.payment_type == 'inbound' and rec.payment_id.partner_type == 'supplier':
                return 'in_invoice'
            elif rec.payment_id.payment_type == 'outbound' and rec.payment_id.partner_type == 'customer':
                return 'out_invoice'
            elif rec.payment_id.payment_type == 'outbound' and rec.payment_id.partner_type == 'supplier':
                return 'in_refund'

    def update_amounts(self, active_id=None):
        """update invoices and outstanding payments with realtime amount"""

        # update open amount and payment residual amount before post to get
        # real-time values
        if active_id:
            self = self.env['account.payment'].browse(active_id)

        # has_group = self.env.user.has_group('account.group_account_manager')
        has_group = self.env.user.has_group('account.group_account_invoice')
        if not has_group:
            raise UserError(
                _("You do not have access to perform this action."))
        if self.is_hide_allocation:
            raise UserError(
                "You can not modify allocation when payment is reconciled with any invoice/bill.")

        self.invoice_lines._get_invoice_data()
        self.outstanding_payment_ids.update_residual_amount()

    def action_post(self):
        """"Override to process multiple invoice using single payment."""
        res = super(AccountPayment, self).action_post()
        for rec in self:
            # check if discount and writeoff account is set
            if rec.discount_amount and not rec.discount_account_id:
                rec.discount_account_id = self.env.company.invoice_discount_account_id.id
                if not rec.discount_account_id:
                    raise ValidationError(
                        _("Please set discount account in configuration menu."))
            if rec.writeoff_amount and not rec.writeoff_account_id:
                # rec.writeoff_account_id = self.env.user.company_id.invoice_writeoff_account_id.id
                rec.writeoff_account_id = self.env.company.invoice_writeoff_account_id.id
                if not rec.writeoff_account_id:
                    raise ValidationError(
                        _("Please set writeoff account in configuration menu."))

            if rec.invoice_lines:
                # rec.action_process_payment_allocation(chatter_log=False)
                rec.cleanup_not_utilized_lines()
        return res

    def cleanup_not_utilized_lines(self):
        # delete not utilized outstanding payment lines
        partial_ids = self.env['account.partial.reconcile'].search([('payment_id', '=', self.id)])
        not_found = self.env['outstanding.payment.line']
        for out_line in self.outstanding_payment_ids:
            if not partial_ids.filtered(lambda p: p.debit_move_id.id == out_line.move_line_id.id or \
                                                  p.credit_move_id.id == out_line.move_line_id.id):
                not_found += out_line

        # not_found.unlink()

    def action_process_payment_allocation(self, chatter_log=True):
        self.env.context = dict(self.env.context)
        self.env.context.update({'is_payment_import': True})
        for rec in self:
            if rec.reconciled_bill_ids or rec.reconciled_invoice_ids:
                raise UserError(
                    "There is already some moves reconciled with this payment. \nHere can not use payment allocation feature.")
            check_amount = False
            if not 'from_payment_import' in self.env.context:
                rec.update_amounts()
            for inv in rec.invoice_lines:
                total_allocation = abs(inv.allocation) + abs(
                    inv.discount_amount) + abs(inv.sale_tax)
                total_allocation = round(total_allocation, 2)
                if not check_amount and total_allocation or inv.select_all:
                    check_amount = True
                if total_allocation > abs(inv.open_amount):
                    raise ValidationError(
                        _("Allocation (discount + allocation), amount must be less than or equal to open amount.\n"
                          "Check invoice %s" % inv.invoice_id.name))
            if not check_amount and chatter_log:
                raise UserError(_("Please allocate amount to invoice lines."))
            for out_line in rec.outstanding_payment_ids:
                total_utilize = round(abs(out_line.amount_to_utilize), 2)
                residual_amount = round(abs(out_line.amount_residual), 2)
                if total_utilize > residual_amount:
                    raise ValidationError(
                        _("Utilization amount should be less then or equal to residual amount.\n"
                          "Check outstanding line %s" % out_line.reference))

            # check if total allocation is more then payment and credit
            outstanding_amount = abs(
                sum(rec.outstanding_payment_ids.filtered(
                    lambda p: p.amount_to_utilize != 0.0).mapped(
                    'amount_to_utilize')))

            total_allocation = abs(sum(rec.invoice_lines.mapped('allocation')))

            # if round(outstanding_amount, 2) > round(total_allocation, 2):
            #     raise ValidationError(
            #         _("Total utilization amount must be less than or equal to allocation amount."
            #           ))

            total_payment = outstanding_amount

            total_allocation = round(total_allocation, 2)
            total_payment = round(total_payment, 2)
            if total_allocation > total_payment:
                raise ValidationError(
                    _("Total allocation amount must be less than or equal to 'payment + outstanding utilization'."))
            rec.with_context(force_edit_move=True)._synchronize_to_moves(
                changed_fields=set({}))

            # if rec.sale_tax or rec.discount_amount or rec.writeoff_amount:
            #     rec.move_id.action_post()

            invoice_lines = rec.invoice_lines.filtered(
                lambda il: il.state == 'draft')
            for line in invoice_lines.filtered(
                    lambda line: line.allocation == 0.0 and line.discount_amount == 0.0 and line.sale_tax == 0.0 and not line.select_all):
                rec.invoice_lines = [(3, line.id)]
                invoice_lines -= line

            for lin in rec.outstanding_payment_ids.filtered(
                    lambda l: l.amount_to_utilize == 0.0):
                rec.outstanding_payment_ids = [(3, lin.id)]

            # check group for account adviser
            # has_group = self.env.user.has_group('account.group_account_manager')
            has_group = self.env.user.has_group('account.group_account_invoice')
            if not has_group and rec.invoice_lines:
                raise AccessError(
                    _("Only account adviser can use payment allocation feature."))

            if rec.payment_type == 'inbound':
                move_line_id = self.env['account.move.line'].search([
                    ('payment_id', '=', rec.id), ('credit', '!=', '0.0'), ('is_extra_line', '=', False)],
                    limit=1)

                writeoff_move_line_id = self.env['account.move.line'].search([
                    ('payment_id', '=', rec.id), ('credit', '!=', '0.0'), ('is_extra_line', '=', True)],
                    limit=1)

                credit_move_id = move_line_id
                writeoff_to_reconcile = self.env['account.move.line']
                if invoice_lines:
                    # here we create dictionary for AR/AP line and its allocation amount, so that partial
                    # payment record created for that line
                    allocation_line_vals = {}
                    invoice_move_line_ids = self.env['account.move.line']
                    if invoice_lines:
                        invoice_move_line_ids, allocation_line_vals, invoice_writeoff_line_ids, writeoff_line_vals = rec.prepare_payment_allocation_vals(
                            invoice_lines)
                        writeoff_to_reconcile = writeoff_move_line_id + invoice_writeoff_line_ids
                    # prepare payment utilization vals and reconcile with invoice lines
                    outstanding_move_ids = rec.outstanding_payment_ids.filtered(
                        lambda p: p.amount_to_utilize != 0.0)
                    total_utilize = sum(
                        outstanding_move_ids.filtered(lambda o: not o.is_current_payment).mapped('amount_to_utilize'))
                    move_allocation = sum(
                        invoice_lines.mapped('allocation'))
                    if round(abs(total_utilize), 2) >= round(
                            abs(move_allocation), 2):
                        to_reconcile = invoice_move_line_ids + \
                                       outstanding_move_ids.mapped(
                                           'move_line_id')
                    else:
                        to_reconcile = credit_move_id + invoice_move_line_ids + \
                                       outstanding_move_ids.mapped('move_line_id')
                    for pay_line in outstanding_move_ids:
                        allocation_line_vals.update({
                            pay_line.move_line_id.id: pay_line.amount_to_utilize})
                    outstanding_payment_ids = outstanding_move_ids.filtered(
                        lambda p: p.move_payment_id and p.amount_to_utilize != 0.0).mapped(
                        'move_line_id')
                    # all_line = credit_move_id + outstanding_move_ids.mapped('move_line_id') + invoice_move_line_ids
                    to_reconcile.with_context(
                        allocation_line_vals=allocation_line_vals,
                        current_payment_id=credit_move_id,
                        payment_id=rec.id,
                        outstanding_payment_ids=outstanding_payment_ids).reconcile()
                    writeoff_to_reconcile.with_context(
                        allocation_line_vals=writeoff_line_vals,
                        current_payment_id=writeoff_move_line_id,
                        payment_id=rec.id,
                        outstanding_payment_ids=writeoff_move_line_id
                    ).reconcile()
                    rec.invoice_lines.write({'state': 'posted'})

            if rec.payment_type == 'outbound':
                move_line_id = self.env['account.move.line'].search([
                    ('payment_id', '=', rec.id), ('debit', '!=', '0.0'), ('is_extra_line', '=', False)],
                    limit=1)
                writeoff_move_line_id = self.env['account.move.line'].search([
                    ('payment_id', '=', rec.id), ('debit', '!=', '0.0'), ('is_extra_line', '=', True)],
                    limit=1)
                debit_move_id = move_line_id

                if invoice_lines:
                    allocation_line_vals = {}
                    invoice_move_line_ids = self.env['account.move.line']
                    if invoice_lines:
                        invoice_move_line_ids, allocation_line_vals, invoice_writeoff_line_ids, writeoff_line_vals = rec.prepare_payment_allocation_vals(
                            invoice_lines)
                        writeoff_to_reconcile = writeoff_move_line_id + invoice_writeoff_line_ids
                    # prepare payment utilization vals and reconcile with invoice lines
                    outstanding_move_ids = rec.outstanding_payment_ids.filtered(
                        lambda p: p.amount_to_utilize != 0.0)

                    total_utilize = sum(
                        outstanding_move_ids.mapped('amount_to_utilize'))
                    move_allocation = sum(invoice_lines.mapped('allocation')) + sum(
                        invoice_lines.mapped('discount_amount')) + \
                                      sum(invoice_lines.mapped('sale_tax')) + \
                                      sum(invoice_lines.filtered(
                                          lambda l: l.payment_difference and l.select_all).mapped(
                                          'payment_difference'))
                    if round(abs(total_utilize), 2) >= round(
                            abs(move_allocation), 2):
                        to_reconcile = invoice_move_line_ids + \
                                       outstanding_move_ids.mapped(
                                           'move_line_id')
                    else:
                        to_reconcile = debit_move_id + invoice_move_line_ids + \
                                       outstanding_move_ids.mapped('move_line_id')
                    for pay_line in outstanding_move_ids:
                        allocation_line_vals.update({
                            pay_line.move_line_id.id: pay_line.amount_to_utilize})
                    outstanding_payment_ids = outstanding_move_ids.filtered(
                        lambda
                            p: p.move_payment_id and p.amount_to_utilize != 0.0).mapped(
                        'move_line_id')
                    to_reconcile.with_context(
                        allocation_line_vals=allocation_line_vals,
                        current_payment_id=debit_move_id,
                        payment_id=rec.id,
                        outstanding_payment_ids=outstanding_payment_ids).reconcile()

                    writeoff_to_reconcile.with_context(
                        allocation_line_vals=writeoff_line_vals,
                        current_payment_id=writeoff_move_line_id,
                        payment_id=rec.id,
                        outstanding_payment_ids=self.env['account.move.line']
                    ).reconcile()

                    rec.invoice_lines.write({'state': 'posted'})
            linked_bill_ids = rec.invoice_lines.mapped('invoice_id').ids
            outstanding_inv_ids = rec.outstanding_payment_ids.filtered(
                lambda l: l.amount_to_utilize != 0.0 and l.move_id).mapped(
                'move_id').ids
            carry_forward_move_ids = rec.outstanding_payment_ids.filtered(
                lambda l: l.amount_to_utilize != 0.0 and l.move_id.related_payment_id).mapped(
                'move_id')
            carry_forward_payment_ids = carry_forward_move_ids.mapped('related_payment_id')
            carry_forward_payment_ids._compute_outstanding_amount()
            linked_bill_ids += outstanding_inv_ids
            for link_id in linked_bill_ids:
                rec.linked_bill_ids = [(4, link_id)]
            if rec.move_id.state == 'posted':
                rec.process_carry_forwarded_moves()
            if chatter_log:
                rec.message_post(
                    body=_("Payment allocation processed successfully."))

    def process_carry_forwarded_moves(self):
        # AR/AP to carry forwarded account
        for rec in self:
            carry_forward_account_id = rec.company_id.carry_forward_account_id
            carry_forward_ml_ids = rec.move_id.line_ids.filtered(lambda l: l.is_carry_forward)
            ar_ap_line_id = carry_forward_ml_ids.filtered(
                lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable'])

            main_ar_ap_line_id = rec.move_id.line_ids.filtered(
                lambda l: not l.is_carry_forward and not l.is_extra_line and l.account_id.account_type in [
                    'asset_receivable', 'liability_payable'])
            if ar_ap_line_id and main_ar_ap_line_id:
                main_ar_ap_line_id += ar_ap_line_id
                main_ar_ap_line_id.reconcile()
            carry_forward_line_id = carry_forward_ml_ids.filtered(
                lambda l: l.account_id.account_type not in ['asset_receivable', 'liability_payable'])
            if carry_forward_line_id.credit:
                carry_debit = carry_forward_line_id.credit
                carry_credit = 0
                ar_credit = carry_forward_line_id.credit
                ar_debit = 0
            elif carry_forward_line_id.debit:
                ar_debit = carry_forward_line_id.debit
                ar_credit = 0
                carry_credit = carry_forward_line_id.debit
                carry_debit = 0
            if not carry_forward_line_id:
                return

            ml_vals = [(0, 0, {
                'account_id': rec.destination_account_id.id,
                'partner_id': rec.partner_id.id,
                'name': rec.name,
                'debit': ar_debit,
                'credit': ar_credit,
                'amount_currency': -(ar_debit or ar_credit),
                'currency_id': rec.currency_id.id,
                'date_maturity': rec.date,
            }),
                       (0, 0, {
                           'account_id': carry_forward_account_id.id,
                           'partner_id': rec.partner_id.id,
                           'name': rec.name,
                           'debit': carry_debit,
                           'credit': carry_credit,
                           'amount_currency': carry_debit or carry_credit,
                           'currency_id': rec.currency_id.id,
                           'date_maturity': rec.date,
                       })]

            # create new move for outstanding payment
            move_vals = {'journal_id': rec.journal_id.id,
                         'date': rec.date,
                         'ref': rec.name,
                         'line_ids': ml_vals,
                         'related_payment_id': rec.id}

            carry_move_id = self.env['account.move'].create(move_vals)

            rec.carry_forward_move_ids = [(4, carry_move_id.id)]
            carry_move_id.action_post()

            # # reconcile moves
            move_to_rec = self.env['account.move.line']
            move_to_rec += carry_move_id.line_ids.filtered(lambda l: l.account_id.account_type not in ['asset_receivable', 'liability_payable'])
            move_to_rec += carry_forward_line_id
            move_to_rec.reconcile()

    def prepare_payment_allocation_vals(self, invoice_lines):
        """this method prepare allocation vals for payment allocation
        @param invoice_lines: invoice lines
        @return: allocation_line_vals"""

        allocation_line_vals = {}
        writeoff_line_vals = {}
        invoice_move_line_ids = self.env['account.move.line']
        invoice_writeoff_line_ids = self.env['account.move.line']
        for inv in invoice_lines:
            if inv.allocation or inv.discount_amount or inv.sale_tax or inv.select_all:
                if inv.select_all:
                    total_allocation = inv.allocation + inv.sale_tax + inv.payment_difference
                    writeoff_amount = inv.discount_amount + inv.sale_tax + inv.payment_difference
                    actual_allocation = inv.allocation
                    for move_line_id in inv.move_line_ids:
                        amount_residual = move_line_id.amount_residual
                        while amount_residual > 0.0:
                            if actual_allocation >= amount_residual:
                                allocation_line_vals.update(
                                    {move_line_id.id: amount_residual})
                                invoice_move_line_ids += move_line_id
                                actual_allocation -= amount_residual
                                amount_residual = 0
                            elif actual_allocation != 0.0:
                                allocation_line_vals.update(
                                    {move_line_id.id: actual_allocation})
                                invoice_move_line_ids += move_line_id
                                amount_residual -= actual_allocation
                                actual_allocation = 0
                            elif writeoff_amount > amount_residual:
                                writeoff_line_vals.update(
                                    {move_line_id.id: amount_residual})
                                invoice_writeoff_line_ids += move_line_id
                                writeoff_amount -= amount_residual
                                amount_residual = 0
                            elif writeoff_amount != 0.0:
                                writeoff_line_vals.update(
                                    {move_line_id.id: writeoff_amount})
                                invoice_writeoff_line_ids += move_line_id
                                amount_residual -= writeoff_amount
                                writeoff_amount = 0
                            else:
                                break

                elif (inv.allocation or inv.sale_tax or inv.select_all) and not inv.discount_amount:
                    total_allocation = inv.allocation + inv.sale_tax
                    actual_allocation = inv.allocation
                    actual_sale_tax = inv.sale_tax
                    for move_line_id in inv.move_line_ids:
                        amount_residual = abs(move_line_id.amount_residual)
                        if abs(total_allocation) >= amount_residual:
                            if actual_allocation >= amount_residual:
                                allocation_line_vals.update(
                                    {move_line_id.id: amount_residual})
                                total_allocation -= move_line_id.amount_residual
                                actual_allocation -= move_line_id.amount_residual
                                invoice_move_line_ids += move_line_id
                            else:
                                allocation_line_vals.update(
                                    {move_line_id.id: actual_allocation})
                                total_allocation -= actual_allocation
                                amount_residual -= actual_allocation
                                actual_allocation -= move_line_id.amount_residual
                                invoice_move_line_ids += move_line_id

                                if actual_sale_tax >= amount_residual:
                                    writeoff_line_vals.update(
                                        {move_line_id.id: amount_residual})
                                    actual_sale_tax -= amount_residual
                                    total_allocation -= amount_residual
                                    invoice_writeoff_line_ids += move_line_id
                                    writeoff_line_vals.update(
                                        {move_line_id.id: amount_residual})
                                    actual_sale_tax -= amount_residual
                                else:
                                    writeoff_line_vals.update(
                                        {move_line_id.id: actual_sale_tax})
                                    actual_sale_tax -= actual_sale_tax
                                    invoice_writeoff_line_ids += move_line_id

                        elif total_allocation != 0.0:
                            if actual_allocation:
                                allocation_line_vals.update(
                                    {move_line_id.id: actual_allocation})
                                invoice_move_line_ids += move_line_id
                            if actual_sale_tax:
                                writeoff_line_vals.update(
                                    {move_line_id.id: actual_sale_tax})
                                invoice_writeoff_line_ids += move_line_id
                            break

                else:
                    total_allocation = inv.allocation + inv.sale_tax
                    actual_allocation = inv.allocation
                    actual_writeoff_amount = inv.sale_tax + inv.discount_amount
                    discount_amount = inv.discount_amount

                    # here we put discount amount in discount move_line_ids and remaining amount in main move_line_id
                    discount_ml_ids = inv.move_line_ids[1:]
                    ml_discount_amount = 0.0
                    if discount_ml_ids:
                        ml_discount_amount = sum(discount_ml_ids.mapped('amount_residual'))
                        if abs(discount_amount) > abs(ml_discount_amount):
                            total_allocation += discount_amount - ml_discount_amount
                            actual_writeoff_amount += discount_amount - ml_discount_amount

                    # prepare allocate discount amount vals

                    for move_line_id in inv.move_line_ids[1:]:
                        if abs(discount_amount) >= abs(move_line_id.amount_residual):
                            writeoff_line_vals.update(
                                {move_line_id.id: move_line_id.amount_residual})
                            discount_amount -= move_line_id.amount_residual
                            invoice_writeoff_line_ids += move_line_id
                        elif discount_amount != 0.0:
                            writeoff_line_vals.update(
                                {move_line_id.id: discount_amount})
                            invoice_writeoff_line_ids += move_line_id
                            break

                    # prepare allocate main amount vals
                    main_ml_id = inv.move_line_ids[:1]
                    if main_ml_id:
                        if actual_allocation:
                            allocation_line_vals.update(
                                {main_ml_id.id: actual_allocation})
                            invoice_move_line_ids += main_ml_id
                        if actual_writeoff_amount:
                            writeoff_line_vals.update({main_ml_id.id: actual_writeoff_amount})
                            invoice_writeoff_line_ids += main_ml_id
        return invoice_move_line_ids, allocation_line_vals, invoice_writeoff_line_ids, writeoff_line_vals

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """override to add discount move line with write off move line"""
        self.ensure_one()
        if not self.invoice_lines:
            return super(AccountPayment, self)._prepare_move_line_default_vals(
                write_off_line_vals=write_off_line_vals)

        # if not self.journal_id.company_id.account_journal_payment_debit_account_id or not self.journal_id.company_id.account_journal_payment_credit_account_id:
        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))

        # Compute amounts.
        write_off_amount_currency = self.writeoff_amount
        discount_amount_currency = self.discount_amount
        sale_tax_currency = self.sale_tax

        carry_forward_amount = 0.0
        # find outstanding amount form current payment
        if self.remaining_amount > self.amount:
            carry_forward_amount = self.amount
        else:
            carry_forward_amount = self.remaining_amount

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
            carry_forward_amount = carry_forward_amount * -1
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
            discount_amount_currency *= -1
            sale_tax_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = discount_amount_currency = sale_tax_currency = 0.0

        write_off_balance = self.currency_id._convert(
            write_off_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )

        discount_balance = self.currency_id._convert(
            discount_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )

        sale_tax_balance = self.currency_id._convert(
            sale_tax_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )

        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency

        counterpart_balance = -liquidity_balance

        if self.payment_type == 'outbound':
            extra_ar_ap_amount = self.writeoff_amount + self.discount_amount + self.sale_tax
            extra_ar_ap_amount_currency = -extra_ar_ap_amount
            carry_forward_amount_currency = -carry_forward_amount
            counter_carry_forward_amount = -carry_forward_amount_currency
        else:
            extra_ar_ap_amount = (self.writeoff_amount + self.discount_amount + self.sale_tax) * -1
            extra_ar_ap_amount_currency = -extra_ar_ap_amount
            carry_forward_amount_currency = carry_forward_amount
            counter_carry_forward_amount = -carry_forward_amount_currency
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else:  # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s',
                                        self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        # payment_display_name = self._prepare_payment_display_name()

        # default_line_name = self.env[
        #     'account.move.line']._get_default_line_name(
        #     _("Internal Transfer") if self.is_internal_transfer else
        #     payment_display_name[
        #         '%s-%s' % (self.payment_type, self.partner_type)],
        #     self.amount,
        #     self.currency_id,
        #     self.date,
        #     partner=self.partner_id,
        # )
        default_line_name = "test"
        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                # 'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                # 'account_id': self.journal_id.company_id.account_journal_payment_credit_account_id.id if liquidity_balance < 0.0 else self.journal_id.company_id.account_journal_payment_debit_account_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference or default_line_name,
                'date_maturity': self.date,
                # 'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },

        ]

        if not self.currency_id.is_zero(extra_ar_ap_amount):
            # extra AR/AP line for writeoff, discount and sale tax
            line_vals_list.append({
                'name': self.payment_reference or default_line_name + ' Extra AR/AP',
                'date_maturity': self.date,
                # 'amount_currency': -extra_ar_ap_amount_currency,
                'currency_id': currency_id,
                'debit': extra_ar_ap_amount if extra_ar_ap_amount > 0.0 else 0.0,
                'credit': -extra_ar_ap_amount if extra_ar_ap_amount < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
                'is_extra_line': True,
            })

        # if not self.currency_id.is_zero(write_off_amount_currency):
        #     # Write-off line.
        #     writeoff_account_id = self.writeoff_account_id
        #     if not writeoff_account_id:
        #         writeoff_account_id = self.env.user.company_id.invoice_writeoff_account_id
        #     line_vals_list.append({
        #         'name': "Write-off",
        #         'amount_currency': write_off_amount_currency,
        #         'currency_id': currency_id,
        #         'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
        #         'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
        #         'partner_id': self.partner_id.id,
        #         'account_id': writeoff_account_id.id,
        #         'is_writeoff': True,
        #     })

        if not self.currency_id.is_zero(write_off_amount_currency):
            # Write-off line.
            writeoff_disc = {}

            # Loop to check different writeoff account to create saperate writeoff lines in JE
            for invoice_line in self.invoice_lines:
                if invoice_line.common_allocation_id.select and invoice_line.common_allocation_id.select_all and invoice_line.common_allocation_id.payment_difference != 0:
                    writeoff_account_id = invoice_line.common_allocation_id.writeoff_account_id
                    if not writeoff_account_id:
                        # writeoff_account_id = self.env.user.company_id.invoice_writeoff_account_id
                        writeoff_account_id = self.env.company.invoice_writeoff_account_id
                    if writeoff_account_id.id not in writeoff_disc:
                        writeoff_disc[writeoff_account_id.id] = invoice_line.common_allocation_id.payment_difference
                    else:
                        writeoff_disc[writeoff_account_id.id] += invoice_line.common_allocation_id.payment_difference

            for list in writeoff_disc:
                write_off_balance = self.currency_id._convert(
                    writeoff_disc[list],
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
                line_vals_list.append({
                    'name': "Write-off",
                    # 'amount_currency': writeoff_disc[list],
                    'currency_id': currency_id,
                    'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
                    'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': list,
                    'is_writeoff': True,
                })

        # if not self.currency_id.is_zero(discount_amount_currency):
        #     # discount line.
        #     discount_account_id = self.discount_account_id
        #     if not discount_account_id:
        #         discount_account_id = self.env.user.company_id.invoice_discount_account_id
        #     line_vals_list.append({
        #         'name': "Discount",
        #         'amount_currency': discount_amount_currency,
        #         'currency_id': currency_id,
        #         'debit': discount_balance if discount_balance > 0.0 else 0.0,
        #         'credit': -discount_balance if discount_balance < 0.0 else 0.0,
        #         'partner_id': self.partner_id.id,
        #         'account_id': discount_account_id.id,
        #         'is_discount': True,
        #     })

        if not self.currency_id.is_zero(discount_amount_currency):
            # discount line.
            discount_disc = {}

            # Loop to check different discount account to create separate discount lines in JE
            for invoice_line in self.invoice_lines:
                if invoice_line.common_allocation_id.select and invoice_line.common_allocation_id.discount_amount != 0:
                    discount_account_id = invoice_line.common_allocation_id.discount_account_id
                    if not discount_account_id:
                        # discount_account_id = self.env.user.company_id.invoice_discount_account_id
                        discount_account_id = self.env.company.invoice_discount_account_id
                    if discount_account_id.id not in discount_disc:
                        discount_disc[discount_account_id.id] = invoice_line.common_allocation_id.discount_amount
                    else:
                        discount_disc[discount_account_id.id] += invoice_line.common_allocation_id.discount_amount
            if discount_disc:

                for list in discount_disc:
                    discount_balance = self.currency_id._convert(
                        discount_disc[list],
                        self.company_id.currency_id,
                        self.company_id,
                        self.date,
                    )
                    line_vals_list.append({
                        'name': "Discount",
                        # 'amount_currency': discount_disc[list],
                        'currency_id': currency_id,
                        'debit': discount_amount_currency if discount_balance > 0.0 else 0.0,
                        'credit': -discount_balance if discount_balance < 0.0 else 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': list,
                        'is_discount': True,
                    })
            else:
                discount_account_id = self.discount_account_id
                if not discount_account_id:
                    # discount_account_id = self.env.user.company_id.invoice_discount_account_id
                    discount_account_id = self.env.company.invoice_discount_account_id
                line_vals_list.append({
                    'name': "Discount",
                    # 'amount_currency': discount_amount_currency,
                    'currency_id': currency_id,
                    'debit': discount_balance if discount_balance > 0.0 else 0.0,
                    'credit': -discount_balance if discount_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': discount_account_id.id,
                    'is_discount': True,
                })
        if not self.currency_id.is_zero(sale_tax_currency):
            line_vals_list.append({
                'name': "Sale Tax",
                # 'amount_currency': sale_tax_currency,
                'currency_id': currency_id,
                'debit': sale_tax_balance if sale_tax_balance > 0.0 else 0.0,
                'credit': -sale_tax_balance if sale_tax_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.sale_tax_account_id.id,
                'is_sale_tax': True,
            })

        # create lines for carry forward account
        if not self.currency_id.is_zero(carry_forward_amount):
            carry_forward_account_id = self.env.company.carry_forward_account_id

            line_vals_list.append({
                'name': "Carry AR/AP Line",
                # 'amount_currency': -carry_forward_amount_currency,
                # 'currency_id': currency_id,
                'debit': -carry_forward_amount if carry_forward_amount < 0.0 else 0.0,
                'credit': carry_forward_amount if carry_forward_amount > 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
                'is_carry_forward': True,
            })

            line_vals_list.append({
                'name': "Carry-forward Line",
                # 'amount_currency': -counter_carry_forward_amount,
                # 'currency_id': currency_id,
                'debit': carry_forward_amount if carry_forward_amount > 0.0 else 0.0,
                'credit': -carry_forward_amount if carry_forward_amount < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': carry_forward_account_id.id,
                'is_carry_forward': True,
            })
        return line_vals_list

    def _seek_for_lines(self):
        ''' override to handle discount and writeoff for multi payment
        '''
        self.ensure_one()

        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']
        discount_lines = self.env['account.move.line']
        sale_tax_lines = self.env['account.move.line']

        for line in self.move_id.line_ids:
            if line.account_id in (
                    self.journal_id.default_account_id,
                    self.payment_method_line_id.payment_account_id,
                    self.journal_id.company_id.account_journal_payment_debit_account_id,
                    self.journal_id.company_id.account_journal_payment_credit_account_id,
                    self.journal_id.inbound_payment_method_line_ids.payment_account_id,
                    self.journal_id.outbound_payment_method_line_ids.payment_account_id,
            ):
                liquidity_lines += line
            elif line.account_id.account_type in (
            'asset_receivable', 'liability_payable') or line.partner_id == line.company_id.partner_id:
                counterpart_lines += line
            elif line.is_discount:
                discount_lines += line
            elif line.is_sale_tax:
                sale_tax_lines += line
            else:
                writeoff_lines += line
        return liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines

    def _synchronize_to_moves(self, changed_fields):
        ''' override to change changed field changed to add invoice_lines field to create writeoff and discount account move line properly.
        and also handle writeoff and discount lines when amount for the same is changed.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return


        if not self._context.get('force_edit_move'):
            if not any(field_name in changed_fields for field_name in (
                    'date', 'amount', 'payment_type', 'partner_type',
                    'payment_reference', 'is_internal_transfer',
                    'currency_id', 'partner_id', 'destination_account_id',
                    'partner_bank_id', 'journal_id', 'invoice_lines'
            )):
                return

        for pay in self.with_context(skip_account_move_synchronization=True):
            if pay.state == 'posted' and not self._context.get(
                    'force_edit_move'):
                continue
            # if pay.state == 'posted' and self._context.get(
            #         'force_edit_move') and pay.sale_tax or pay.discount_amount or pay.writeoff_amount:
            #     pay.move_id.button_draft()

            liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if liquidity_lines and counterpart_lines and writeoff_lines:
                # for writeoff and discount lines, we need to create a new
                # account move line with the same amount and currency
                counterpart_amount = sum( counterpart_lines.mapped('amount_currency'))
                if self.invoice_lines:
                    writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))
                if self.invoice_lines or 'invoice_lines' in changed_fields:
                    writeoff_amount = self.writeoff_amount

                # To be consistent with the payment_difference made in account.payment.register,
                # 'writeoff_amount' needs to be signed regarding the 'amount' field before the write.
                # Since the write is already done at this point, we need to
                # base the computation on accounting values.
                if self.invoice_lines:
                    if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                        sign = -1
                    else:
                        sign = 1
                    writeoff_amount = abs(writeoff_amount) * sign

                    write_off_line_vals = {
                        'name': writeoff_lines[0].name,
                        'amount': writeoff_amount,
                        'account_id': writeoff_lines[0].account_id.id,
                    }
                else:
                    write_off_line_vals = {}
            else:
                write_off_line_vals = {}

            # if liquidity_lines and counterpart_lines and discount_lines:
            #     # code for discount
            #     counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
            #     discount_amount = sum(discount_lines.mapped('amount_currency'))
            #     if self.invoice_lines or 'invoice_lines' in changed_fields:
            #         discount_amount = self.discount_amount
            #     # To be consistent with the payment_difference made in account.payment.register,
            #     # 'discount_amount' needs to be signed regarding the 'amount' field before the write.
            #     # Since the write is already done at this point, we need to base the computation on accounting values.
            #     if (counterpart_amount > 0.0) == (discount_amount > 0.0):
            #         sign = -1
            #     else:
            #         sign = 1
            #     discount_amount = abs(discount_amount) * sign
            #
            #     discount_line_vals = {
            #         'name': discount_lines[0].name,
            #         'amount': discount_amount,
            #         'account_id': discount_lines[0].account_id.id,
            #     }
            # else:
            #     discount_line_vals = {}
            #
            # if liquidity_lines and counterpart_lines and sale_tax_lines:
            #     # code for discount
            #     counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
            #     sale_tax = sum(sale_tax_lines.mapped('amount_currency'))
            #     if self.invoice_lines or 'invoice_lines' in changed_fields:
            #         sale_tax = self.sale_tax
            #     # To be consistent with the payment_difference made in account.payment.register,
            #     # 'discount_amount' needs to be signed regarding the 'amount' field before the write.
            #     # Since the write is already done at this point, we need to base the computation on accounting values.
            #     if (counterpart_amount > 0.0) == (sale_tax > 0.0):
            #         sign = -1
            #     else:
            #         sign = 1
            #     sale_tax = abs(sale_tax) * sign
            #
            #     sale_tax_line_vals = {
            #         'name': discount_lines[0].name,
            #         'amount': sale_tax,
            #         'account_id': discount_lines[0].account_id.id,
            #     }
            # else:
            #     sale_tax_line_vals = {}
            line_vals_list = pay._prepare_move_line_default_vals(
                write_off_line_vals=write_off_line_vals)
            context = dict(self.env.context)
            line_ids_commands = []
            if len(liquidity_lines) == 1:
                line_ids_commands.append(
                    (1, liquidity_lines.id, line_vals_list[0]))
            else:
                for line in liquidity_lines:
                    line_ids_commands.append((2, line.id, 0))
                line_ids_commands.append((0, 0, line_vals_list[0]))

            if len(counterpart_lines) == 1:
                line_ids_commands.append(
                    (1, counterpart_lines.id, line_vals_list[1]))
            else:
                for line in counterpart_lines:
                    line_ids_commands.append((2, line.id, 0))
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for line in discount_lines:
                line_ids_commands.append((2, line.id))

            for line in sale_tax_lines:
                line_ids_commands.append((2, line.id))
            if pay.state == 'posted':
                for extra_line_vals in line_vals_list[2:]:
                    line_ids_commands.append((0, 0, extra_line_vals))
                    extra_line = False
                    balance = 0
                    amount_currency = 0
                    if extra_line_vals['credit'] > 0 and 'date_maturity' in extra_line_vals:
                        balance = -extra_line_vals['credit']
                        amount_currency = -extra_line_vals['credit']
                        extra_line = True
                    elif 'is_discount' in extra_line_vals and extra_line_vals['is_discount']:
                        balance = extra_line_vals['debit']
                        amount_currency = extra_line_vals['debit']
                        extra_line = True
                    elif 'is_writeoff' in extra_line_vals and extra_line_vals['is_writeoff'] and not 'extra_charge_lines' in context:
                        balance = extra_line_vals['debit']
                        amount_currency = extra_line_vals['debit']
                        extra_line = True
                    if extra_line:
                        extra_line_vals.update({
                            'move_id': pay.move_id.id,
                            'display_type': 'product',
                            'move_name': pay.move_id.name,
                            'company_id': pay.move_id.company_id.id,
                            'date': pay.date,
                            'parent_state': 'posted',
                            'balance': balance,
                            'amount_currency': amount_currency

                        })
                        if 'extra_charge_lines' in context:
                            extra_line_ctx = {'extra_charge_lines': context['extra_charge_lines']}
                            pay.with_context(extra_line_ctx).create_extra_lines(extra_line_vals)
                        else:
                            pay.create_extra_lines(extra_line_vals)

            elif pay.state == 'draft':
                # Update the existing journal items.
                # If dealing with multiple write-off lines, they are dropped and a
                # new one is generated.
                pay.move_id.write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })

    def create_extra_lines(self, extra_line_vals):
        if extra_line_vals:
            context = dict(self.env.context)
            extra_line_ctx = {}
            if 'extra_charge_lines' in context:
                extra_line_ctx = context['extra_charge_lines']
            if 'credit' in extra_line_vals and extra_line_vals['credit'] > 0:
                move_ids = self.invoice_lines.mapped('invoice_id')
                inv_move_lines = move_ids.mapped('line_ids').filtered(lambda la: la.account_id.account_type == 'asset_receivable')
                payment_move_line = self.invoice_line_ids.filtered(lambda la: la.account_id.account_type == 'asset_receivable')
                credit = self.amount + extra_line_vals['credit']
                balance = -credit
                amount_currency = -credit
                amount_residual = -credit
                self.env.cr.execute(
                    "UPDATE account_move_line SET credit = %s, balance = %s, amount_currency = %s, "
                    "amount_residual = %s WHERE id in %s", (credit, balance, amount_currency, amount_residual, tuple(payment_move_line.ids)))
                # self.env.cr.commit()
            else:
                disc_amount = extra_line_vals['debit']
                extra_line_vals['debit'] = disc_amount
                extra_line_vals['balance'] = disc_amount
                extra_line_vals['amount_currency'] = disc_amount
                extra_line_vals.update({
                    'payment_id': self.id,
                    'create_date': datetime.datetime.now(),
                    'create_uid': self.env.uid,
                    'journal_id': self.journal_id.id
                })
                values = tuple(extra_line_vals.values())
                ml_id = self.move_id.line_ids.filtered(lambda l: l.is_extra_line)
                if ml_id:
                    self.env.cr.execute("DELETE FROM account_move_line WHERE id in %s", (tuple(ml_id.ids),))
                self.env.cr.execute(
                    """
                    INSERT INTO account_move_line(name, currency_id, debit, credit, partner_id, account_id, 
                    is_extra_line, move_id, display_type, move_name, company_id, date, parent_state, balance, 
                    amount_currency, payment_id, create_date, create_uid, journal_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, values)
                # self.env.cr.commit()
                for ext_line in extra_line_ctx:
                    if ext_line:
                        extra_line_vals['name'] = ext_line
                        charge_type = self.env['account.charges.type'].search([('name', '=', ext_line)], limit=1)
                        if not charge_type or not charge_type.account_id:
                            raise UserError(_(F"Charge Type not defined for {ext_line}"))
                        payment_ext_line = self.env['account.move.line']
                        extra_line_vals['debit'] = extra_line_ctx[ext_line]
                        extra_line_vals['balance'] = extra_line_ctx[ext_line]
                        extra_line_vals['amount_currency'] = extra_line_ctx[ext_line]
                        extra_line_vals['account_id'] = charge_type.account_id.id
                        values = tuple(extra_line_vals.values())
                        self.env.cr.execute(
                            """
                            INSERT INTO account_move_line(name, currency_id, debit, credit, partner_id, account_id, 
                            is_extra_line, move_id, display_type, move_name, company_id, date, parent_state, balance, 
                            amount_currency, payment_id, create_date, create_uid, journal_id) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, values)
                        # self.env.cr.commit()

    def _synchronize_from_moves(self, changed_fields):
        ''' override to add discount lines when seeking for lines called from _synchronize_from_moves
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization
            # will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(
                        _("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1 or len(
                        counterpart_lines.filtered(lambda l: not l.is_extra_line and not l.is_carry_forward)) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal entry must always contains:\n"
                        "- one journal item involving the outstanding payment/receipts account.\n"
                        "- one journal item involving a receivable/payable account.\n"
                        "- optional journal items, all sharing the same account.\n\n"
                    ) % move.display_name)

                if writeoff_lines.filtered(lambda l: not l.is_extra_line and not l.is_carry_forward) and len(
                        writeoff_lines.filtered(
                                lambda l: not l.is_extra_line and not l.is_carry_forward).account_id) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, all the write-off journal items must share the same account."
                    ) % move.display_name)

                if discount_lines and len(discount_lines.account_id) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, all the discount journal items must share the same account."
                    ) % move.display_name)

                if sale_tax_lines and len(sale_tax_lines.account_id) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, all the sale tax journal items must share the same account."
                    ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in
                       all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in
                       all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if not pay.is_internal_transfer:
                    if counterpart_lines.account_id.account_type == 'asset_receivable':
                        payment_vals_to_write['partner_type'] = 'customer'
                    else:
                        payment_vals_to_write['partner_type'] = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(
                move._cleanup_write_orm_values(
                    move, move_vals_to_write))
            pay.write(
                move._cleanup_write_orm_values(pay, payment_vals_to_write))

    @api.depends('move_id.line_ids.amount_residual',
                 'move_id.line_ids.amount_residual_currency',
                 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' override to handle discount lines for multiple payment.
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using
                    # the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(
                        sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (
                        counterpart_lines +
                        writeoff_lines +
                        discount_lines +
                        sale_tax_lines).filtered(
                    lambda line: line.account_id.reconcile)

                pay.is_reconciled = pay.currency_id.is_zero(
                    sum(reconcile_lines.mapped(residual_field)))

    def action_open_manual_reconciliation_widget(self):
        ''' override to handle discount parameter in seek for line return value.
        Note: its odoo enterprise method.
        '''
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Payments without a customer can't be matched"))

        liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = self._seek_for_lines()

        action_context = {'company_ids': self.company_id.ids,
                          'partner_ids': self.partner_id.ids}
        if self.partner_type == 'customer':
            action_context.update({'mode': 'customers'})
        elif self.partner_type == 'supplier':
            action_context.update({'mode': 'suppliers'})

        if counterpart_lines:
            action_context.update({'move_line_id': counterpart_lines[0].id})

        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    @api.depends('move_id.line_ids.matched_debit_ids',
                 'move_id.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        res = super(AccountPayment,
                    self)._compute_stat_buttons_from_reconciliation()
        stored_payments = self.filtered('id')
        for pay in stored_payments:
            partial_ids = self.env['account.partial.reconcile'].search(
                [('payment_id', '=', pay.id)])
            move_ids = partial_ids.mapped('debit_move_id').mapped(
                'move_id') + partial_ids.mapped('credit_move_id').mapped(
                'move_id')
            move_ids = self.env['account.move'].search(
                [('id', 'in', move_ids.ids), ('move_type', '!=', 'entry')])
            if move_ids and move_ids[0].move_type in self.env['account.move'].get_sale_types(True):
                pay.reconciled_invoice_ids += move_ids
                pay.reconciled_invoices_count = len(pay.reconciled_invoice_ids)
            elif pay.linked_bill_ids and pay.linked_bill_ids[0].move_type in \
                    self.env[
                        'account.move'].get_purchase_types(True):
                pay.reconciled_bill_ids += move_ids
                pay.reconciled_bills_count = len(pay.reconciled_bill_ids)
        return res

    def action_open_common_view(self, active_id=None):
        if active_id:
            self = self.browse(active_id)
        if self.is_hide_allocation and active_id:
            raise UserError(
                "You can not modify allocation when payment is reconciled with any invoice/bill.")
        common_ids = self.env['common.allocation'].search([('linked_payment_id', '=', self.id)])

        # has_group = self.env.user.has_group('account.group_account_manager')
        has_group = self.env.user.has_group('account.group_account_invoice')

        if self.is_hide_allocation or not has_group:
            return {
                'name': _('Payment Allocation'),
                'view_mode': 'tree',
                'res_model': 'common.allocation',
                'view_id': self.env.ref('invoice_multi_payment.view_common_invoice_allocation_form').id,
                'type': 'ir.actions.act_window',
                'res_ids': common_ids.ids,
                'domain': [('linked_payment_id', '=', self.id)],
                'flags': {'hasSelectors': False},
                'target': 'new',
            }


        if not common_ids or active_id:
            self.update_invoice_lines()
        common_all_obj = self.env['common.allocation']
        common_ids = self.env['common.allocation']
        commona_list = []
        for line in self.invoice_lines.filtered(lambda a: not a.common_allocation_id):
            common_id = self.env['common.allocation'].search([('invoice_line_id', '=', line.id)])
            if common_id:
                continue
            common_vals = {
                'reference': line.invoice_id.name,
                'invoice_line_id': line.id,
                'invoice_id': line.invoice_id.id,
                'date': line.date,
                'total_amount': line.total_amount,
                'amount_residual': line.open_amount,
                'allocation': line.allocation,
                'discount_amount': line.discount_amount,
                'amount_allowed_discount': line.amount_allowed_discount,
                'sale_tax': line.sale_tax,
                'payment_difference': line.payment_difference,
                'select_all': line.select_all,
                'is_outstanding_line': False,
                'linked_payment_id': self.id,
                'move_line_ids': [(6, 0, line.move_line_ids.ids)],
                'state': line.state,
            }
            commona_list.append(common_vals)
            # common_id = common_all_obj.create(common_vals)
            # common_ids += common_id
            # line.common_allocation_id = common_id.id

        if commona_list:
            common_create_ids = common_all_obj.create(commona_list)
            common_ids += common_create_ids
            for common in common_create_ids:
                payment_line = self.env['payment.invoice.line'].browse(common.invoice_line_id.id)
                payment_line.common_allocation_id = common.id

        outstanding_commona_list = []
        for outstanding_line in self.outstanding_payment_ids:
            common_id = self.env['common.allocation'].search([('outstanding_line_id', '=', outstanding_line.id)])
            if common_id:
                continue
            is_payment_line = False
            amount_residual = 0
            if outstanding_line.move_payment_id.id == self.id:
                is_payment_line = True
                amount_residual = outstanding_line.amount_residual

            common_vals = {
                'linked_payment_id': self.id,
                'move_id': outstanding_line.move_id.id,
                'reference': outstanding_line.move_id.name or outstanding_line.move_payment_id.name,
                'outstanding_line_id': outstanding_line.id,
                'move_line_id': outstanding_line.move_line_id.id,
                'date': outstanding_line.payment_date,
                'amount_residual': outstanding_line.amount_residual,
                'allocation': amount_residual,
                'is_outstanding_line': True,
                'select': is_payment_line,
                'is_payment_line': is_payment_line,
            }
            outstanding_commona_list.append(common_vals)

        if outstanding_commona_list:
            outstanding_common_ids = common_all_obj.create(outstanding_commona_list)
            common_ids += outstanding_common_ids
            for outstanding_line in outstanding_common_ids:
                outstanding_line.outstanding_line_id.common_allocation_id = outstanding_line.id

        self.update_amounts()
        return {
            'name': _('Payment Allocation'),
            'view_mode': 'tree',
            'res_model': 'common.allocation',
            'view_id': self.env.ref('invoice_multi_payment.view_common_invoice_allocation_form').id,
            'type': 'ir.actions.act_window',
            'res_ids': common_ids.ids,
            'domain': [('linked_payment_id', '=', self.id)],
            'flags': {'hasSelectors': False},
            'target': 'self',
        }

    def action_open_carry_forward_moves(self):
        move_ids = self.mapped('carry_forward_move_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['context'] = {'search_default_misc_filter': False}
        if len(move_ids) > 1:
            action['domain'] = [('id', 'in', move_ids.ids)]
        elif len(move_ids) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = move_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    @api.depends('invoice_lines', 'state', 'payment_allocation')
    def _compute_carry_forward_bool_move(self):
        for payment in self:
            # payment.update({
            #     'carry_forward_count': len(payment.carry_forward_move_ids)
            #     })
            payment.update({
                'carry_forward_count': len(payment.carry_forward_move_ids.filtered(lambda s: 'posted' in s.mapped('state')))
            })

    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        """"Override to process internal transfer."""
        for payment in self:
            if payment.is_internal_transfer:
                payment._compute_partner_id()
        res = super(AccountPayment, self)._compute_is_internal_transfer()
        for payment in self:
            payment.is_internal_transfer = payment.partner_id \
                                           and payment.partner_id == payment.journal_id.company_id.partner_id
        return res

    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        """"Override to process internal transfer."""
        if 'is_payment' in self._context and self._context.get('is_payment') !=False:
            for payment in self:
                if payment.is_internal_transfer:
                    payment._compute_partner_id()
            res = super(AccountPayment, self)._compute_is_internal_transfer()
            for payment in self:
                payment.is_internal_transfer = payment.partner_id \
                                               and payment.partner_id == payment.journal_id.company_id.partner_id
            return res
        return super(AccountPayment, self)._compute_is_internal_transfer()

    def allocation_invoice_import(self, active_id=None):
        if active_id:
            self = self.env['account.payment'].browse(active_id)

        if len(self.linked_bill_ids) > 0:
            raise UserError(_("Invoices already imported for this payment!"))

        form_view_id = self.env.ref('invoice_multi_payment.account_invoice_credit_allocation_import_form')
        if form_view_id:
            return {
                'name': 'Import Invoice In Allocation',
                'type': 'ir.actions.act_window',
                'res_model': 'account.invoice.allocation.import',
                'view_mode': 'form',
                'view_id': form_view_id.id,
                'target': 'new',
                'context': {'default_account_payment_id': self.id},
            }


