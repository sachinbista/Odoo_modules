##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

import logging

from odoo import models, fields, _
from odoo.exceptions import UserError
from .. import shopify

_logger = logging.getLogger('Shopify Payout')


class ShopifyPayout(models.Model):

    _name = "shopify.payout"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Shopify Payout"

    name = fields.Char(size=256)
    shopify_config_id = fields.Many2one(
        'shopify.config', string="Shopify Configuration")
    payout_ref_id = fields.Char(
        string="Payout Reference", help="The unique reference of the payout")
    date_payout = fields.Date(help="The date the payout was issued.")
    payout_transaction_ids = fields.One2many('shopify.payout.line', 'payout_id',
                                             string="Payout transaction lines")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', help="currency of the payout.")
    amount_total = fields.Float(
        string="Total Amount", help="The total amount of the payout.")
    statement_id = fields.Many2one(
        'account.bank.statement', string="Bank Statement")
    payout_status = fields.Selection([('scheduled', 'Scheduled'), ('in_transit', 'In Transit'), ('paid', 'Paid'),
                                      ('failed', 'Failed'), ('cancelled', 'Cancelled')],
                                     help="The transfer status of the payout. The value will be one of the following\n"
                                          "- Scheduled:  The payout has been created and had transactions assigned to"
                                          "it, but it has not yet been submitted to the bank\n"
                                          "- In Transit: The payout has been submitted to the bank for processing.\n"
                                          "- Paid: The payout has been successfully deposited into the bank.\n"
                                          "- Failed: The payout has been declined by the bank.\n"
                                          "- Cancelled: The payout has been canceled by Shopify")
    status = fields.Selection([('draft', 'Draft'), ('partially_generated', 'Partially Generated'),
                               ('generated', 'Generated'), ('partially_processed',
                                                            'Partially Processed'),
                               ('processed', 'Processed'), ('validated', 'Validated')], string="Status",
                              default="draft")

    def shopify_import_payouts(self, shopify_config, start_date, end_date):
        """This method is used to create queue and queue line for payouts"""
        error_log_env = self.env['shopify.error.log'].sudo()
        queue_line_id = self.env.context.get('queue_line_id', False)
        shopify_config.check_connection()
        # _logger.info("Import Payout Reports....")
        try:
            payouts = shopify.Payouts().find(status="paid", date_min=start_date,
                                             date_max=end_date, limit=250)
        except Exception as error:
            error_message = "Something is wrong while import the payout records : {0}".format(
                error)
            error_log_env.sudo().create_update_log(
                shopify_config_id=shopify_config,
                operation_type='import_payouts',
                shopify_log_line_dict={'error': [
                    {'error_message': error_message,
                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]}
            )
            return False

        payouts = self.create_payouts(payouts, shopify_config)
        payouts = payouts.sorted(key=lambda x: x.id, reverse=True)

        self._cr.commit()
        # _logger.info(
        #     "Payout Reports are Created. Generating Bank statements...")
        # for payout in payouts:
        #     payout.generate_bank_statement()

        shopify_config.write({'last_payout_import_date': end_date})
        # _logger.info("Payout Reports are Imported.")
        return True

    def create_payouts(self, payout_reports, shopify_config):
        """This method is used to create records of Payout report from the data."""
        payouts = self
        for payout_report in payout_reports:
            payout_data = payout_report.to_dict()
            payout_id = payout_data.get('id')
            payout = self.search([('shopify_config_id', '=', shopify_config.id),
                                  ('payout_ref_id', '=', payout_id)])
            if payout:
                # _logger.info("Existing Payout Report found for %s.", payout_id)
                payouts += payout
                continue
            payout_vals = self.prepare_payout_vals(payout_data, shopify_config)
            payout = self.create(payout_vals)

            if not payout:
                continue
            payouts += payout
            # _logger.info(
            #     "Payout Report created for %s. Importing Transaction lines..", payout_id)
            payout.create_payout_lines(payout_data)

        return payouts

    def prepare_payout_vals(self, data, shopify_config):
        """Based on payout data prepare payout vals."""
        currency_obj = self.env['res.currency']
        payout_reference_id = data.get('id')
        payout_date = data.get('date', '')
        payout_status = data.get('status', '')
        currency = data.get('currency', '')
        amount = data.get('amount', 0.0)

        payout_vals = {
            'payout_ref_id': payout_reference_id,
            'date_payout': payout_date,
            'payout_status': payout_status,
            'amount_total': amount,
            'shopify_config_id': shopify_config.id
        }
        currency_id = currency_obj.search([('name', '=', currency)], limit=1)
        if currency_id:
            payout_vals.update({'currency_id': currency_id.id})
        return payout_vals

    def create_payout_lines(self, payout_data):
        """Gets Payout Transactions and creates transaction lines from that."""
        shopify_payout_line_obj = self.env['shopify.payout.line']

        transactions = shopify.Transactions().find(
            payout_id=self.payout_ref_id, limit=250)

        for transaction in transactions:
            transaction_data = transaction.to_dict()
            transaction_vals = self.prepare_transaction_vals(
                transaction_data, self.shopify_config_id)
            if transaction_vals.get('transaction_type') != 'payout':
                shopify_payout_line_obj.create(transaction_vals)

        # Create fees line
        fees_amount = float(payout_data.get('summary').get('charges_fee_amount', 0.0)) + float(
            payout_data.get('summary').get('refunds_fee_amount', 0.0)) + float(
            payout_data.get('summary').get('adjustments_fee_amount', 0.0))
        shopify_payout_line_obj.create({
            'payout_id': self.id or False,
            'transaction_type': 'fees',
            'amount': -fees_amount,
            'fee': 0.0,
            'net_amount': fees_amount,
            'is_remaining_statement': True
        })
        # _logger.info("Transaction lines are added for %s.", self.payout_ref_id)
        return True

    def prepare_transaction_vals(self, data, shopify_config):
        """Use : Based on transaction data prepare transaction vals."""
        currency_obj = self.env['res.currency']
        sale_order_obj = self.env['sale.order'].sudo()
        transaction_id = data.get('id', '')
        source_order_id = data.get('source_order_id', '')
        transaction_type = data.get('type', '')
        amount = data.get('amount', 0.0)
        fee = data.get('fee', 0.0)
        net_amount = data.get('net', 0.0)
        currency = data.get('currency', '')

        order_id = False
        if source_order_id:
            order_id = sale_order_obj.search([('shopify_order_id', '=', source_order_id),
                                              ('shopify_config_id', '=', shopify_config.id)],
                                             limit=1)

        transaction_vals = {
            'payout_id': self.id or False,
            'transaction_id': transaction_id,
            'source_order_id': source_order_id,
            'transaction_type': transaction_type,
            'order_id': order_id and order_id.id,
            'amount': amount,
            'fee': fee,
            'net_amount': net_amount,
            'is_remaining_statement': True
        }

        currency_id = currency_obj.search([('name', '=', currency)], limit=1)
        if currency_id:
            transaction_vals.update({'currency_id': currency_id.id})

        return transaction_vals

    def generate_bank_statement(self):
        bank_statement_obj = self.env['account.bank.statement']
        journal = self.check_journal_and_currency()
        if not journal:
            return False

        bank_statement_id = bank_statement_obj.search(
            [('shopify_payout_ref', '=', self.payout_ref_id)], limit=1)
        if bank_statement_id:
            self.write({'statement_id': bank_statement_id.id})
            return True

        name = '{0}_{1}'.format(
            self.shopify_config_id.name, self.payout_ref_id)
        vals = {
            'shopify_payout_ref': self.payout_ref_id,
            'company_id': self.shopify_config_id.default_company_id.id,
            'journal_id': journal.id,
            'name': name,
            'date': self.date_payout,
            'balance_start': 0.0,
            'balance_end_real': 0.0
        }
        bank_statement_id = bank_statement_obj.create(vals)
        # _logger.info(
        #     "Bank Statement Generated for Shopify Payout : %s.", self.payout_ref_id)
        self.create_bank_statement_lines_for_payout(bank_statement_id)
        if self.check_process_statement():
            status = 'generated'
        else:
            status = 'partially_generated'

        # _logger.info("Lines are added in Bank Statement %s.", name)
        self.write({'statement_id': bank_statement_id.id, 'status': status})

        return True

    def check_journal_and_currency(self):
        """This method checks for configured journal and its currency."""
        journal = self.shopify_config_id.shopify_payout_journal_id
        if not journal:
            message_body = "Please configure Payout Journal in shopify configuration."
            self.message_post(body=_(message_body))
            return False
            raise UserError(_(message_body))

        currency_id = journal.currency_id.id or self.shopify_config_id.default_company_id.currency_id.id or False
        if currency_id != self.currency_id.id:
            message_body = "The Report currency and currency in Journal/Shopify Cnfiguration are different." \
                           "\nMake sure the Report currency and the Journal/Shopify Cnfiguration currency must be same."
            self.message_post(body=_(message_body))
            raise UserError(_(message_body))
        return journal

    def check_process_statement(self):
        """This method visible/Invisible the statement execution button."""
        all_statement_processed = True
        if self.payout_transaction_ids and any(line.is_remaining_statement for line in self.payout_transaction_ids):
            all_statement_processed = False
        return all_statement_processed

    def generate_remaining_bank_statement(self):
        partner_obj = self.env['res.partner'].sudo()
        bank_statement_line_obj = self.env['account.bank.statement.line'].sudo(
        )
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        account_payment_obj = self.env['account.payment'].sudo()
        sale_order_obj = self.env["sale.order"].sudo()

        transaction_ids = self.payout_transaction_ids
        regenerate = True
        if regenerate:
            transaction_ids = self.payout_transaction_ids.filtered(
                lambda line: line.is_remaining_statement)
        for transaction in transaction_ids:
            order_id = transaction.order_id
            if transaction.transaction_type in ['charge', 'refund', 'payment_refund'] and not order_id:
                source_order_id = transaction.source_order_id
                order_id = sale_order_obj.search([('shopify_order_id', '=', source_order_id),
                                                  ('shopify_config_id', '=', self.shopify_config_id.id)],
                                                 limit=1)
                if order_id:
                    transaction.order_id = order_id
                else:
                    error_message = "Transaction line {0} will not automatically reconcile due to " \
                        "order {1} is not found in odoo.".format(
                            transaction.transaction_id, transaction.source_order_id)
                    error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                           shopify_log_line_dict={'error': [
                                                               {'error_message': error_message,
                                                                'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                    queue_line_id and queue_line_id.write({'state': 'failed'})
                    # We can not use shopify order reference here because it may create duplicate name,
                    # and name of journal entry should be unique per company. So here I have used transaction Id
                    bank_line_vals = {
                        'name': transaction.transaction_id,
                        'payment_ref': transaction.transaction_id,
                        'date': self.date_payout,
                        'amount': transaction.amount,
                        'statement_id': self.statement_id.id,
                        'shopify_transaction_id': transaction.transaction_id,
                        "shopify_transaction_type": transaction.transaction_type,
                        'sequence': 1000
                    }
                    bank_statement_line_obj.create(bank_line_vals)
                    transaction.is_remaining_statement = False
                    continue

            partner = partner_obj._find_accounting_partner(order_id.partner_id)

            domain, invoice, shop_error_log_id = self.check_for_invoice_refund(
                transaction)
            if domain:
                payment_reference = account_payment_obj.search(domain, limit=1)

                if payment_reference:
                    reference = payment_reference.name
                    if not regenerate:
                        payment_aml_rec = payment_reference.line_ids.filtered(
                            lambda line: line.account_type in ('asset_cash', 'liability_credit_card'))
                        reconciled, log_line = self.check_reconciled_transactions(
                            transaction, payment_aml_rec)
                        if reconciled:
                            # shop_error_log_id += shop_error_log_id
                            continue
                else:
                    reference = invoice.name or ''
            else:
                # shop_error_log_id += shop_error_log_id
                reference = transaction.order_id.name

            if transaction.amount:
                name = False
                if transaction.transaction_type not in ['charge', 'refund', 'payment_refund']:
                    reference = transaction.transaction_type + "/"
                    if transaction.transaction_id:
                        reference += transaction.transaction_id
                    else:
                        reference += self.payout_ref_id
                else:
                    if order_id.name:
                        name = transaction.transaction_type + "_" + \
                            order_id.name + "/" + transaction.transaction_id
                bank_line_vals = {
                    'name': name or reference,
                    'payment_ref': reference,
                    'date': self.date_payout,
                    'partner_id': partner and partner.id,
                    'amount': transaction.amount,
                    'statement_id': self.statement_id.id,
                    'sale_order_id': order_id.id,
                    'shopify_transaction_id': transaction.transaction_id,
                    'shopify_transaction_type': transaction.transaction_type,
                    'journal_id': transaction.payout_id.check_journal_and_currency().id,
                }

                if invoice and invoice.move_type == "out_refund":
                    bank_line_vals.update({"refund_invoice_id": invoice.id})
                bank_statement_line_obj.create(bank_line_vals)
                if regenerate:
                    transaction.is_remaining_statement = False

        if self.check_process_statement():
            state = 'generated'
        else:
            state = 'partially_generated'
        self.write({'status': state})
        return True

    def create_bank_statement_lines_for_payout(self, bank_statement_id, regenerate=False):
        """This method creates bank statement lines from the transaction lines of Payouts."""
        partner_obj = self.env['res.partner'].sudo()
        bank_statement_line_obj = self.env['account.bank.statement.line'].sudo(
        )
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        account_payment_obj = self.env['account.payment'].sudo()
        sale_order_obj = self.env["sale.order"].sudo()

        transaction_ids = self.payout_transaction_ids.filtered(
                lambda line: line.is_remaining_statement)
        for transaction in transaction_ids:
            order_id = transaction.order_id
            if transaction.transaction_type in ['charge', 'refund', 'payment_refund'] and not order_id:
                source_order_id = transaction.source_order_id
                order_id = sale_order_obj.search([('shopify_order_id', '=', source_order_id),
                                                  ('shopify_config_id', '=', self.shopify_config_id.id)],
                                                 limit=1)
                if order_id:
                    transaction.order_id = order_id
                else:
                    error_message = "Transaction line {0} will not automatically reconcile due to " \
                        "order {1} is not found in odoo.".format(
                            transaction.transaction_id, transaction.source_order_id)
                    error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                           shopify_log_line_dict={'error': [
                                                               {'error_message': error_message,
                                                                'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                    queue_line_id and queue_line_id.write({'state': 'failed'})
                    # We can not use shopify order reference here because it may create duplicate name,
                    # and name of journal entry should be unique per company. So here I have used transaction Id
                    bank_line_vals = {
                        'name': transaction.transaction_id,
                        'payment_ref': transaction.transaction_id,
                        'date': self.date_payout,
                        'amount': transaction.amount,
                        'statement_id': bank_statement_id.id,
                        'shopify_transaction_id': transaction.transaction_id,
                        "shopify_transaction_type": transaction.transaction_type,
                        'sequence': 1000,
                        'journal_id': transaction.payout_id.check_journal_and_currency().id,
                    }
                    bank_statement_line_obj.create(bank_line_vals)
                    transaction.is_remaining_statement = False
                    continue

            partner = partner_obj._find_accounting_partner(order_id.partner_id)

            domain, invoice, shop_error_log_id = self.check_for_invoice_refund(
                transaction)
            if domain:
                payment_reference = account_payment_obj.search(domain, limit=1)

                if payment_reference:
                    reference = payment_reference.name
                    if not regenerate:
                        payment_aml_rec = payment_reference.line_ids.filtered(
                            lambda line: line.account_type in ('asset_cash', 'liability_credit_card'))
                        reconciled, log_line = self.check_reconciled_transactions(
                            transaction, payment_aml_rec)
                        if reconciled:
                            # shop_error_log_id += shop_error_log_id
                            continue
                else:
                    reference = invoice.name or ''
            else:
                # shop_error_log_id += shop_error_log_id
                reference = transaction.order_id.name

            if transaction.amount:
                name = False
                if transaction.transaction_type not in ['charge', 'refund', 'payment_refund']:
                    reference = transaction.transaction_type + "/"
                    if transaction.transaction_id:
                        reference += transaction.transaction_id
                    else:
                        reference += self.payout_ref_id
                else:
                    if order_id.name:
                        name = transaction.transaction_type + "_" + \
                            order_id.name + "/" + transaction.transaction_id
                bank_line_vals = {
                    'name': name or reference,
                    'payment_ref': reference,
                    'date': self.date_payout,
                    'partner_id': partner and partner.id,
                    'amount': transaction.amount,
                    'statement_id': bank_statement_id.id,
                    'sale_order_id': order_id.id,
                    'shopify_transaction_id': transaction.transaction_id,
                    'shopify_transaction_type': transaction.transaction_type,
                    'journal_id': transaction.payout_id.check_journal_and_currency().id,
                }

                if invoice and invoice.move_type == "out_refund":
                    bank_line_vals.update({"refund_invoice_id": invoice.id})
                bank_statement_line = bank_statement_line_obj.create(bank_line_vals)
                if bank_statement_line:
                    transaction.is_remaining_statement = False
        return True

    def shopify_view_bank_statement(self):
        """This function is used to show generated bank statement."""
        self.ensure_one()
        action = self.env.ref('account.action_bank_statement_tree', False)
        form_view = self.env.ref('account.view_bank_statement_form', False)
        result = action and action.read()[0] or {}
        result['views'] = [(form_view and form_view.id or False, 'form')]
        result['res_id'] = self.statement_id and self.statement_id.id or False
        return result

    def check_for_invoice_refund(self, transaction):
        """This method is used to search for invoice or refund and then prepare domain as that."""
        invoice_ids = self.env["account.move"].sudo()
        domain = []
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        order_id = transaction.order_id

        if transaction.transaction_type == 'charge':
            invoice_ids = order_id.invoice_ids.filtered(lambda x:
                                                        x.state == 'posted' and x.move_type == 'out_invoice' and
                                                        x.amount_total == transaction.amount)
            if not invoice_ids:
                error_message = "Invoice is not created for order %s in odoo" % \
                    (order_id.name or transaction.source_order_id)
                shop_error_log_id = error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                           shopify_log_line_dict={'error': [
                                                                               {'error_message': error_message,
                                                                                'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                queue_line_id and queue_line_id.write({'state': 'failed'})
                # transaction.is_remaining_statement = True
                return domain, invoice_ids, shop_error_log_id
            domain += [('amount', '=', transaction.amount),
                       ('payment_type', '=', 'inbound')]
        elif transaction.transaction_type in ['refund', 'payment_refund']:
            invoice_ids = order_id.invoice_ids.filtered(lambda x:
                                                        x.state == 'posted' and x.move_type == 'out_refund' and
                                                        x.amount_total == -transaction.amount)
            if not invoice_ids:
                error_message = "In Shopify Payout, there is a Refund, but Refund is not created for order %s in" \
                    "odoo" % (order_id.name or transaction.source_order_id)
                shop_error_log_id = error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                           shopify_log_line_dict={'error': [
                                                                               {'error_message': error_message,
                                                                                'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                # transaction.is_remaining_statement = True
                return domain, invoice_ids, shop_error_log_id
            domain += [('amount', '=', -transaction.amount),
                       ('payment_type', '=', 'outbound')]

        domain.append(('ref', 'in', invoice_ids.mapped("payment_reference")))
        return domain, invoice_ids, shop_error_log_id

    def check_reconciled_transactions(self, transaction, aml_rec=False):
        """This method is used to check if the transaction line already reconciled or not."""
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        reconciled = False
        if aml_rec and aml_rec.statement_id:
            error_message = 'Transaction line %s is already reconciled.' % transaction.transaction_id
            shop_error_log_id = error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                       shopify_log_line_dict={'error': [
                                                                           {'error_message': error_message,
                                                                            'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.write({'state': 'failed'})
            reconciled = True
        return reconciled, shop_error_log_id

    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                'shopify.payout') or _('New')
        result = super(ShopifyPayout, self).create(vals)
        return result


class ShopifyPayoutLine(models.Model):

    _name = "shopify.payout.line"
    _description = "Shopify Payout Lines"
    _rec_name = "transaction_id"

    payout_id = fields.Many2one(
        'shopify.payout', string="Payout ID", ondelete="cascade")
    transaction_id = fields.Char(
        string="Transaction ID", help="The unique identifier of the transaction.")
    source_order_id = fields.Char(string="Order Reference ID", help="The id of the Order that this transaction  "
                                                                    "ultimately originated from")
    transaction_type = fields.Selection(
        [('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
         ('reserve', 'Reserve'), ('adjustment',
                                  'Adjustment'), ('credit', 'Credit'),
         ('debit', 'Debit'), ('payout',
                              'Payout'), ('payout_failure', 'Payout Failure'),
         ('payout_cancellation', 'Payout Cancellation'), ('fees', 'Fees'), ('payment_refund', 'Payment Refund')],
        help="The type of the balance transaction", string="Balance Transaction Type")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', help="currency code of the payout.")
    source_type = fields.Selection(
        [('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
         ('reserve', 'Reserve'), ('adjustment', 'Adjustment'), ('payout', 'Payout'), ],
        help="The type of the balance transaction", string="Resource Leading Transaction")
    amount = fields.Float(
        string="Amount", help="The gross amount of the transaction.")
    fee = fields.Float(
        string="Fees", help="The total amount of fees deducted from the transaction amount.")
    net_amount = fields.Float(
        string="Net Amount", help="The net amount of the transaction.")
    order_id = fields.Many2one('sale.order', string="Order Reference")
    processed_date = fields.Datetime("Processed Date")
    is_processed = fields.Boolean("Processed?")
    is_remaining_statement = fields.Boolean(string="Is Remaining Statement?")
