# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _
import datetime
from odoo.exceptions import UserError


class PaymentInvoiceLine(models.Model):
    _name = 'payment.invoice.line'
    _description = "Multiple Payment Invoice Lines"
    _order = 'payment_date asc,id'
    _rec_name = 'invoice'

    payment_id = fields.Many2one('account.payment', string="Payment", ondelete="cascade")
    move_id = fields.Many2one('account.move', string="Discount Move")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    move_line_id = fields.Many2one('account.move.line', string="Invoice Line")
    invoice_date = fields.Date(string="Invoice Date")
    payment_date = fields.Date(string='Due Date')
    invoice = fields.Char(related='invoice_id.name', string="Invoice Number")
    date = fields.Date(compute='_get_invoice_data',
                       store=True)
    total_amount = fields.Monetary(string='Total',
                                   compute='_get_invoice_data',
                                   currency_field='invoice_currency_id',
                                   store=True,
                                   )
    open_amount = fields.Monetary(string='Due',
                                  compute='_get_invoice_data',
                                  currency_field='invoice_currency_id',
                                  store=True,
                                  )
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="payment_id.currency_id",
                                  string="Currency", readonly=True, store=True)
    invoice_currency_id = fields.Many2one(related="invoice_id.currency_id",
                                          string="Invoice Cur.", store=True)
    allocation = fields.Monetary(string='Allocation',
                                 currency_field='currency_id', default=0.0)
    converted_currency_amount = fields.Monetary(string='Due (Cur.)',
                                                currency_field='currency_id',
                                                compute='_get_currency_amount',
                                                store=True)
    discount_amount = fields.Monetary(string='Applied Disc.',
                                      currency_field='invoice_currency_id')
    payment_difference = fields.Monetary(
        string='Payment Difference',
        compute='_get_payment_difference',
        store=True,
        currency_field='currency_id')

    select_all = fields.Boolean(string="Mark As Paid")
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')],
                             string='Status', default='draft')
    select = fields.Boolean(string="Select")
    sale_tax = fields.Monetary(string='Sale Tax',
                                      currency_field='invoice_currency_id')
    move_line_ids = fields.Many2many('account.move.line', 'rel_payment_allocation_move_line_ids', 'allocation_line_id', 'move_line_id',
                                     string="Move Lines", copy=False)
    amount_allowed_discount = fields.Monetary(string='Allowed Disc.',
                                        currency_field='currency_id',
                                       compute='_get_invoice_data',
                                        store=True)
    common_allocation_id = fields.Many2one('common.allocation', string="Common Allocation")


    def write(self, vals):
        res = super(PaymentInvoiceLine, self).write(vals)

        if self._context.get('from_common'):
            return res
        # update allocation in common line
        if 'open_amount' in vals and self.common_allocation_id:
            self.common_allocation_id.with_context(from_payment=True).amount_residual = vals['open_amount']

        if 'allocation' in vals and self.common_allocation_id:
            self.common_allocation_id.with_context(from_payment=True).allocation = vals['allocation']
            self.common_allocation_id.onchange_make_select_all()

        if 'discount_amount' in vals and self.common_allocation_id:
            self.common_allocation_id.with_context(from_payment=True).discount_amount = vals['discount_amount']
            self.common_allocation_id.onchange_make_select_all()

        if 'sale_tax' in vals and self.common_allocation_id:
            self.common_allocation_id.with_context(from_payment=True).sale_tax = vals['sale_tax']
            self.common_allocation_id.onchange_make_select_all()

        if 'state' in vals and self.common_allocation_id:
            self.common_allocation_id.with_context(from_payment=True).state = vals['state']

        if 'select_all' in vals and self.common_allocation_id:
            self.common_allocation_id.with_context(from_payment=True).select_all = vals['select_all']

        return res

    def unlink(self):
        for rec in self:
            if rec.common_allocation_id:
                rec.common_allocation_id.unlink()
        return super(PaymentInvoiceLine, self).unlink()

    @api.onchange('select')
    def onchange_select(self):
        if not self.select:
            self.update({'allocation': 0.0,
                         'discount_amount': 0.0,
                         'sale_tax': 0.0,})

    @api.onchange('allocation')
    def onchange_allocation_sign(self):
        if self.open_amount < 0:
            self.allocation = abs(self.allocation) * -1
        else:
            self.allocation = abs(self.allocation)

    @api.onchange('discount_amount')
    def onchange_discount_amount_sign(self):
        # change allocation amount if discount amount is greater than open amount
        total_allocation = abs(self.discount_amount) + abs(self.allocation) + abs(self.sale_tax)
        if total_allocation > abs(self.open_amount):
            self.allocation = abs(self.open_amount) - abs(self.discount_amount) - abs(self.sale_tax)
            self.onchange_allocation_sign()

        if self.open_amount < 0:
            self.discount_amount = abs(self.discount_amount) * -1
        else:
            self.discount_amount = abs(self.discount_amount)

    @api.onchange('sale_tax')
    def onchange_sale_tax_amount_sign(self):
        if self.open_amount < 0:
            self.sale_tax = abs(self.sale_tax) * -1
        else:
            self.sale_tax = abs(self.sale_tax)

    @api.onchange('discount_amount', 'allocation', 'sale_tax')
    def onchange_make_select_all(self):
        self.onchange_discount_amount_sign()
        self.onchange_sale_tax_amount_sign()
        self.onchange_allocation_sign()
        total = self.discount_amount + self.allocation + self.sale_tax
        total = round(total, 2)
        if total == self.open_amount:
            self.select_all = True
        else:
            self.select_all = False
        allocation = abs(self.discount_amount) + \
            abs(self.allocation) + abs(self.sale_tax)
        allocation = round(allocation, 2)
        if allocation == 0.0:
            self.select = False
        else:
            self.select = True
        if abs(allocation) > abs(self.open_amount):
            raise UserError(_('You can not allocate more than open amount.'))

    @api.depends('allocation', 'open_amount', 'discount_amount', 'sale_tax')
    def _get_payment_difference(self):
        for rec in self:
            rec.payment_difference = rec.open_amount - \
                rec.allocation - rec.discount_amount - rec.sale_tax

    @api.depends('invoice_id')
    def _get_invoice_data(self):
        for invoice_line in self:
            move_line_ids = invoice_line.move_line_ids.filtered(lambda m: m.amount_residual != 0.0)
            balance = sum(move_line_ids.mapped('balance'))

            invoice_line.amount_allowed_discount = 0
            invoice_id = invoice_line.invoice_id
            invoice_line.date = invoice_id.invoice_date
            invoice_line.total_amount = balance
            # invoice_line.move_line_ids = [(6, 0, move_line_ids.ids)]

            if invoice_line.invoice_id.state == 'posted':
                if invoice_line.invoice_id.invoice_payment_term_id:
                    discount_percentage = 0.0
                    discount_days = 0
                    for invoice_payment_line_id in invoice_line.invoice_id.invoice_payment_term_id.line_ids:
                        if invoice_payment_line_id.discount_percentage > 0.0:
                            discount_percentage = invoice_payment_line_id.discount_percentage
                            discount_days = invoice_payment_line_id.discount_days
                            break

                    if discount_percentage > 0.0 and discount_days == 0:
                        if invoice_line.invoice_id.invoice_date == invoice_line.payment_id.date:
                            invoice_line.amount_allowed_discount = (invoice_line.invoice_id.amount_residual / 100) * discount_percentage

                    if discount_percentage > 0.0 and discount_days > 0:
                        discount_days = invoice_line.invoice_id.invoice_date + datetime.timedelta(discount_days)
                        if invoice_line.payment_id.date >= invoice_line.invoice_id.invoice_date and invoice_line.payment_id.date <= discount_days:
                            invoice_line.amount_allowed_discount = (invoice_line.invoice_id.amount_residual / 100) * discount_percentage

                # amount_residual = sum(move_line_ids.mapped('amount_residual'))
                # invoice_line.open_amount = amount_residual
                # # check for allowed discount
                # main_ml_id = invoice_line.move_line_ids[:1]
                # if len(invoice_line.move_line_ids) > 1:
                #     if invoice_line.payment_id.date and main_ml_id.date_maturity >= invoice_line.payment_id.date:
                #         discount_ml_ids = invoice_line.move_line_ids[1:]
                #         invoice_line.amount_allowed_discount = sum(discount_ml_ids.mapped('amount_residual'))
            else:
                invoice_line.open_amount = 0.0
            if invoice_line.open_amount == 0.0:
                invoice_line.payment_id.invoice_lines = [(3, invoice_line.id)]

    @api.depends('open_amount', 'payment_id.currency_id')
    def _get_currency_amount(self):
        company_id = self.env.user.company_id
        for invoice_line in self:
            if invoice_line.open_amount != 0 and invoice_line.payment_id.currency_id:
                amount_currency = invoice_line.invoice_currency_id._convert(
                    invoice_line.open_amount, invoice_line.payment_id.currency_id, company_id,
                    invoice_line.payment_id.date or fields.Date.today())
                invoice_line.converted_currency_amount = amount_currency

    @api.onchange('select_all')
    def onchange_select_toggle(self):
        if self.payment_id.check_all_posted:
            raise UserError(
                _('You can not change allocation lines because all invoices are posted.'))

    def _onchange_select_all(self, select_all=False):
        for rec in self:
            if select_all and not rec.allocation:
                allocation = abs(rec.open_amount) - \
                    abs(rec.discount_amount) - abs(rec.sale_tax)
                if rec.payment_id.remaining_amount >= abs(allocation):
                    allowed_amount = allocation
                else:
                    allowed_amount = abs(
                        rec.allocation) + rec.payment_id.remaining_amount
                if rec.open_amount < 0 and allowed_amount >= abs(
                        rec.open_amount):
                    rec.write({
                        'allocation': allocation * -1,
                         'select': True})
                    # rec.allocation = allocation * -1
                elif rec.open_amount > 0 and allowed_amount >= abs(rec.open_amount):
                    rec.write({
                        'allocation': allocation,
                        'select': True})
                    # rec.allocation = allocation
                elif rec.open_amount < 0 and allowed_amount <= abs(rec.open_amount):
                    rec.write({
                        'allocation': allowed_amount * -1,
                        'select': True})
                    # rec.allocation = allowed_amount * -1
                elif rec.open_amount > 0 and allowed_amount <= abs(rec.open_amount):
                    rec.write({
                        'allocation': allowed_amount,
                        'select': True})
                    # rec.allocation = allowed_amount
                rec.select_all = select_all
