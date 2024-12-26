# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

import logging
import mimetypes
from base64 import b64decode, b64encode

import base64
import csv
from datetime import datetime, timedelta
from io import StringIO
import os
from odoo import _, api, fields, models, exceptions
from odoo.exceptions import UserError, ValidationError
import xlrd

_logger = logging.getLogger(__name__)


csv_columns =['Invoice Number','Partner','P/O Number','Invoice Date', 'Invoice Description','Gross Amount','Discount Amount','Net Amount','Discount Account','GL Account','Analytic Account','Analytic Distribution']


class importpayment_errorlines(models.TransientModel):
    _name = 'importpayment.errorlines'
    _description = 'Show error logs after import payment'

    importpayment_id = fields.Many2one('account.payment.import', 'Error Line')
    rowline = fields.Integer('Row number')
    comment = fields.Text('Exception')


class AccountPaymentImport(models.TransientModel):
    _name = "account.payment.import"
    _description = "Account Payment Import from CSV"

    csv_import = fields.Boolean(default=True, readonly=True)
    payment_file = fields.Binary(
        string="Import XLSX File",
        required=True,
        help="Upload a Request for Payment. Supported "
        "formats: CSV.",
    )
    payment_filename = fields.Char(string="Filename")
    is_new_invoice = fields.Boolean("Allow New Entry", default=True)
    is_vendor_bill = fields.Boolean("Is Vendor Bill",default=False)
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', domain="[('type', 'in', ['bank','cash'])]",help="This field is ignored in a bank statement reconciliation.", check_company=True)
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             readonly=False, store=True,
                                             compute='_compute_payment_method_line_id',
                                             domain="[('id', 'in', available_payment_method_line_ids)]",
                                             help="Manual: Pay or Get paid by any method outside of Odoo.\n"
                                                  "Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
                                                  "Check: Pay bills by check and print it from Odoo.\n"
                                                  "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
                                                  "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
                                                  "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n", required=True)
    payment_method_code = fields.Char(related="payment_method_line_id.code")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',compute='_compute_payment_method_line_fields')
    payment_date = fields.Date(string="Date", default=fields.Date.today, required=True)
    communication = fields.Char(string="Memo")
    check_number = fields.Char(string="Check Number")
    import_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='xls')

    @api.depends('journal_id')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines('customer')

    @api.depends('journal_id')
    def _compute_payment_method_line_id(self):
        for wizard in self:
            available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines('customer')

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False

    check_number_dict = {}
    def _get_template(self):
        '''Get import payment template for downloading '''
        attachment = self.env['ir.attachment'].search([('res_model','=','AccountPaymentImport'),('name','=','Import Payment Template.xlsx')],limit=1)
        if not any(attachment):
            attach_obj = self.env['ir.attachment']
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
            if not path:
                raise exceptions.Warning(_("No path found!"))
            filepath = path.replace("/wizard", "/static/src/file/Import Payment Template.xlsx")
            file = open(filepath, 'rb').read()

            attachment = attach_obj.create({
                'res_model': 'AccountPaymentImport',
                'type': 'binary',
                'name': 'Import Payment Template.xlsx',
                'db_datas': file,
            })
        return attachment

    delimeter = fields.Char('Delimeter', default=',',help='Default delimeter is ","')
    exception = fields.Boolean('Exception Found', default=False)
    noexception = fields.Boolean('Exception not found', default=False)
    errorline_ids = fields.One2many('importpayment.errorlines', 'importpayment_id', string='Error lines')
    state = fields.Selection([('exception', 'exception'),
                              ('noexception', 'noexception')], 'State')

    def pay_discount(self, payment_values, values):
        '''
            Pay discount
        '''
        payment_values.update({'payment_difference': round(float(self.validate_amountvalue(values['Discount Amount'])), 2)})
        return payment_values

    def pay_check(self, payment_values, values):
        '''
        pay check
        '''
        payment_values.update({'communication': int(values['Check Number'])})
        return payment_values

    def allow_check_number(self, check_no, partner_id):
        '''Find check number to assign any other partner or not.'''
        check_res = True
        check_lst = []
        if self.check_number_dict:
            for v in self.check_number_dict.values():
                check_lst.extend(v)
            if check_no in check_lst:
                for k, v in self.check_number_dict.items():
                    if partner_id != k and check_no in v:
                        check_res = False
            elif check_no not in check_lst:
                self.check_number_dict.update(
                    {partner_id: list(set(self.check_number_dict.get(partner_id, []) + [check_no]))})
            # if check_res and not self.check_number_dict.has_key(partner_id):
            #     self.check_number_dict.update({partner_id: [check_no]})
        else:
            self.check_number_dict.update({partner_id: [check_no]})
        return check_res

    def validate_date(self, date_text):
        '''
        Accept following date format:
            1) mm-dd-yyyy
            2) yyyy-dd-mm
        '''
        try:
            datetime.strptime(date_text, '%m-%d-%Y')
            return dict(format='%m-%d-%Y')
        except ValueError:
            try:
                datetime.strptime(date_text, '%Y-%d-%m')
                return dict(format='%Y-%d-%m')
            except ValueError:
                '''return false '''
            return False

    def validate_amountvalue(self, amount_value):
        try:
            if type(amount_value) is str:
                amount_value = amount_value.replace('$','')
                amount_value = amount_value.replace(',','')
            amount = round(float(amount_value), 2)
        except ValueError:
            return False
        return amount

    def get_sale_journal_entry(self, journal_entry_number):
        '''check if direct sale journal entry created '''
        # For payment import they are serching this number with tph Inv number
        # Which will store in ref field.  So I have change the search.
        # move_id = self.env['account.move'].search([('ref', '=', journal_entry_number)], limit=1)
        self._cr.execute('''SELECT id FROM account_move
                            WHERE name='%s' LIMIT 1
                        ''' % (journal_entry_number))
        datas = self._cr.fetchone()
        move_id = []
        if datas:
            move_id = self.env['account.move'].browse(datas[0])
        return move_id

    def get_tph_invoice(self, tph_invoice_id, account_ids):
        """Get invoice by csv TPH invoice number(Customer)."""
        account_move_line_obj = self.env['account.move.line']
        tph_moves_ids = []
        if account_ids:
            self._cr.execute('''SELECT id FROM account_move_line
                                WHERE name = %s or ref=%s
                                AND account_id in %s LIMIT 1
                            ''', (tph_invoice_id, tph_invoice_id, account_ids))
            datas = self._cr.fetchone()
            if datas:
                tph_moves_ids = datas[0]
        return tph_moves_ids

    def get_invoice(self, invoice_number, invoice_vals={}, dryrun=False):
        """Get invoice id by csv invoice number."""
        invoice_ids = []
        if invoice_vals:
            for invoice_val in invoice_vals:
                self._cr.execute('''SELECT id FROM account_move WHERE name='%s' or ref='%s' or po_reference='%s' LIMIT 1''' % (invoice_val, invoice_val, invoice_val))
                datas = self._cr.fetchone()
                if datas:
                    invoice_ids.append(datas[0])
                elif self.is_new_invoice:
                    partner = self.env['res.partner'].sudo().search(['|','|',('name', '=', invoice_vals[invoice_val]['partner']),('name', '=', invoice_vals[invoice_val]['partner'].capitalize()),('name', '=', invoice_vals[invoice_val]['partner'].upper())])
                    if not partner:
                        partner = self.env['res.partner'].sudo().create({'name':invoice_vals[invoice_val]['partner']})

                    date = self.parse_date(invoice_vals[invoice_val]['invoice_date'])

                    journal_id = self.env['account.journal'].search([('name', '=', 'Customer Invoices')],limit=1)
                    gross_amount = self.validate_amountvalue(invoice_vals[invoice_val]['gross_amount'])
                    move_type = 'out_invoice'
                    if gross_amount < 0:
                        move_type = 'out_refund'
                    if self.is_vendor_bill:
                        move_type = 'in_refund'
                        journal_id = self.env['account.journal'].search([('name', '=', 'Vendor Bills')], limit=1)
                        if gross_amount < 0:
                            move_type = 'in_invoice'
                    lines = []
                    for invoice_line in invoice_vals[invoice_val]['invoice_lines']:
                        gross_amount = self.validate_amountvalue(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['gross_amount'])
                        discount_amount = self.validate_amountvalue(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['discount_amount'])
                        net_amount = self.validate_amountvalue(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['net_amount'])
                        lines.append((0, 0, {
                                'name': invoice_vals[invoice_val]['invoice_lines'][invoice_line]['description'],
                                'quantity': 1,
                                'price_unit': abs(gross_amount),
                                'account_id': int(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['income_account_id']),
                                'tax_ids': [(6, 0, [])],
                                'analytic_distribution': invoice_vals[invoice_val]['invoice_lines'][invoice_line]['analytic_distribution'],

                            }))

                    invoice = self.env['account.move'].sudo().create({
                        'partner_id': partner.id,
                        'ref': invoice_val,
                        'date': date,
                        'invoice_date': date,
                        'move_type': move_type,
                        'journal_id': journal_id.id,
                        'invoice_line_ids': lines,
                    })
                    if not dryrun:
                        invoice.sudo().action_post()
                    invoice_ids.append(invoice.id)
        else:
            self._cr.execute('''SELECT id FROM account_move WHERE name='%s' or ref='%s' LIMIT 1''' % (invoice_number, invoice_number))
            datas = self._cr.fetchone()
            if datas:
                invoice_ids = datas[0]

        return invoice_ids

    def get_signed_amount(self, sale_journal_entry, receivable_account_ids):
        """Get total invoice signed amount."""
        amount_total_signed = [0.0]
        if sale_journal_entry and sale_journal_entry.journal_id and sale_journal_entry.journal_id.type == 'purchase':
            self.env.cr.execute('''SELECT COALESCE(sum(credit-debit), 0.0) FROM account_move_line
                                    WHERE move_id=%s AND account_id in %s
                                ''', (sale_journal_entry.id, receivable_account_ids))
            amount_total_signed = [self.env.cr.fetchone()[0]]
        else:
            self.env.cr.execute('''SELECT COALESCE(sum(debit-credit), 0.0) FROM account_move_line
                                    WHERE move_id=%s AND account_id in %s
                                ''', (sale_journal_entry.id, receivable_account_ids))
            amount_total_signed = [self.env.cr.fetchone()[0]]
        return amount_total_signed

    def get_csv_file_data(self):
        data = {}
        file_name = self.payment_filename.split('.')
        if file_name[-1] != 'csv':
            raise exceptions.ValidationError(_("Not a valid file!"))
        data = base64.b64decode(self.payment_file)
        file_input = StringIO(data.decode("utf-8"))
        file_input.seek(0)
        reader_info = []
        if self.delimeter:
            delimeter = str(self.delimeter)
        else:
            delimeter = ','
        reader = csv.reader(file_input, delimiter=delimeter, lineterminator='\r\n')
        try:
            reader_info.extend(reader)
        except Exception:
            raise exceptions.ValidationError(_("Not a valid file!"))
        keys = reader_info[0]
        # CHECK IF KEYS EXIST
        if not isinstance(keys, list):
            raise exceptions.ValidationError(_("%s\nColumns not found in sheet") % ', '.join(csv_columns))
        keys_not_exist = filter(lambda x: x not in csv_columns, keys)
        if any(keys_not_exist):
            raise exceptions.ValidationError(
                _("%s\nColumns not found in sheet") % ', '.join(keys_not_exist))
        del reader_info[0]
        return reader_info,keys

    def get_excel_file_data(self):
        data = {}
        try:
            file_data = base64.b64decode(self.payment_file)
            book = xlrd.open_workbook(file_contents=file_data)
        except FileNotFoundError:
            raise UserError('No such file or directory found. \n%s.' % self.payment_filename)
        except xlrd.biffh.XLRDError:
            raise UserError('Only excel files are supported.')
        for sheet in book.sheets():
            try:
                line_vals = []
                keys = []
                # if sheet.name == 'Sheet1':
                for row in range(sheet.nrows):
                    if row >= 1:
                        row_values = sheet.row_values(row)
                        line_vals.append(row_values)
                    else:
                        keys = sheet.row_values(row)
            except IndexError:
                pass
        return line_vals,keys


    def action_validate_button(self):
        error_line_vals = self.action_import_payment(dryrun=True)
        context = self.env.context
        if any(error_line_vals) and (context.get('validate') or context.get('account.payment.import')):
            self.env.cr.execute('''delete from importpayment_errorlines where importpayment_id=%s ''', (self.id,))
            self.exception = True
            _logger.info("Errors encountered.Payment cannot be initiated")
            self.errorline_ids = error_line_vals
            self.payment_file, self.payment_filename, self.state = '', '', 'exception'
            self.noexception = False
        else:
            self.env.cr.execute('''delete from importpayment_errorlines where importpayment_id=%s ''', (self.id,))
            self.noexception, self.exception, self.state = True, False, 'noexception'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.import',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    # TODO: add tests
    def action_import_payment(self, dryrun=False):
        """ This function is use to import payment from CSV file."""
        self.ensure_one()

        context = self.env.context
        invoice_obj = self.env['account.move']
        payment_obj = self.env['account.payment']
        journal_obj = self.env['account.journal']
        account_obj = self.env['account.account']
        analytic_account_obj = self.env['account.analytic.account']
        user_obj = self.env['res.users']
        payment_method_obj = self.env['account.payment.method.line']
        register_payment_obj = self.env['account.payment.register']
        partner_obj = self.env['res.partner']
        account_move_line_obj = self.env['account.move.line']
        error_line_vals = []
        invoices_ids = []
        journal_entry_ids = []
        payment_list = []
        used_discount_move_lst = []
        rownumber = 1
        pay_type = 'inbound'
        mimetype = None
        company = self.env.user.company_id
        res_config_obj = self.env['ir.config_parameter'].sudo()

        discount_account_id = res_config_obj.get_param('bs_register_payment_discount_account_id', default=False)
        browse_discount_account_id = self.env['account.account'].browse(int(discount_account_id))
        if browse_discount_account_id.company_id != company:discount_account_id = account_obj.search([('name', '=', browse_discount_account_id.name), ('code', '=', browse_discount_account_id.code),('company_id', '=', company.id)], limit=1).id

        writeoff_account_id = res_config_obj.get_param('bs_register_payment_discount_account_id', default=False)
        browse_writeoff_account_id = self.env['account.account'].browse(int(writeoff_account_id))
        if browse_writeoff_account_id.company_id != company:
            writeoff_account_id = account_obj.search([('name', '=', browse_writeoff_account_id.name), ('code', '=', browse_writeoff_account_id.code),('company_id', '=', company.id)], limit=1).id

        payment_method_id = self.payment_method_line_id
        journal_id = self.journal_id


        if not discount_account_id:
            error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                           'comment': 'Discount Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.' , \
                                           'rowline': ''}])

        if not writeoff_account_id:
            error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                           'comment': 'Write Off Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.' , \
                                           'rowline': ''}])

        if not self.payment_file:
            raise exceptions.Warning(_("You need to select a file!"))
            # DECODE THE FILE DATA

        if self.import_option == 'csv':
            reader_info,keys = self.get_csv_file_data()
        else:
            reader_info,keys = self.get_excel_file_data()

            # file_name = self.payment_filename.split('.')
            # if file_name[-1] != 'csv':
            #     raise exceptions.ValidationError(_("Not a valid file!"))
            # data = base64.b64decode(self.payment_file)
            # file_input = StringIO(data.decode("utf-8"))
            # file_input.seek(0)
            # reader_info = []
            # if self.delimeter:
            #     delimeter = str(self.delimeter)
            # else:
            #     delimeter = ','
            # reader = csv.reader(file_input, delimiter=delimeter, lineterminator='\r\n')
            # try:
            #     reader_info.extend(reader)
            # except Exception:
            #     raise exceptions.ValidationError(_("Not a valid file!"))
            # keys = reader_info[0]
            # # CHECK IF KEYS EXIST
            # if not isinstance(keys, list):
            #     raise exceptions.ValidationError(_("%s\nColumns not found in sheet") % ', '.join(csv_columns))
            # keys_not_exist = filter(lambda x: x not in csv_columns, keys)
            # if any(keys_not_exist):
            #     raise exceptions.ValidationError(
            #         _("%s\nColumns not found in sheet") % ', '.join(keys_not_exist))
            # del reader_info[0]
        values = {}
        # receivable_account_ids = tuple([account.id for account in self.env["account.account"].sudo().search(
        #     [("user_type_id", "=", "Receivable")])])
        self._cr.execute('''SELECT id FROM account_account WHERE account_type IN ('asset_receivable', 'liability_payable')''')
        account_ids = [accounts[0] for accounts in self._cr.fetchall()]
        receivable_account_ids = tuple(account_ids)

        # """Create not exist invoice with multiple lines"""
        invoice_data = {}
        if len(reader_info) < 1:
            raise exceptions.ValidationError(_("No data found in this file to import!"))

        self._cr.execute('SAVEPOINT paymentimport')
        for i in range(len(reader_info)):
            commercial_partner_id = False
            val = {}
            rownumber += 1
            payment_vals = {}
            field = reader_info[i]
            is_journal_entry = False
            sale_journal_entry = False
            invoice = False
            # values = dict(zip(keys, [field_val.strip() if type(field_val) == str else field_val for field_val in field]))
            # Assuming 'keys' is a list of headers and 'field' is a list of corresponding values
            values = dict(
                (key.strip(), field_val.strip() if type(field_val) == str else field_val) for key, field_val in
                zip(keys, field))

            if (('Invoice Number' in values and values['Invoice Number'] == '') and ('P/O Number' in values and values['P/O Number'] == '')) or ('Invoice Date' in values and values['Invoice Date'] == '') or ('Gross Amount' in values and values['Gross Amount'] == '') or ('Net Amount' in values and values['Net Amount'] == ''):
                error_line_vals.append([0, 0, {'importpayment_id': self.id, 'comment': 'There is some problem in this line %s' % (
                                                    values['Invoice Number']), 'rowline': rownumber}])
            # Check Analytic Account
            analytic_distribution = {}
            if 'Analytic Account' in values and values['Analytic Account'] != '':
                analytic_account_id = analytic_account_obj.with_company(company).search(['|',('name', '=', values['Analytic Account']),('code', '=', values['Analytic Account'])])
                if not analytic_account_id:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Analytic Account %s not found for invoice %s' % (
                                                   values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(analytic_account_id) > 1:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Duplicate Analytic Account %s found for invoice %s' % (
                                                       values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])
                if len(analytic_account_id) == 1:
                    analytic_distribution = {analytic_account_id.id: 100}

                if 'Analytic Distribution' in values and not values['Analytic Distribution']:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, 'comment': 'Analytic Distribution %s found for invoice %s' % (
                                                       values['Analytic Distribution'], values['Invoice Number']), 'rowline': rownumber}])

            if 'GL Account' in values and values['GL Account'] != '':
                gl_account = str(values['GL Account'])
                gl_account = gl_account.split('.')[0]
                gl_account = gl_account.split(',')[0]

                income_account_id = account_obj.with_company(company).search(['|',('name', '=', gl_account),('code', '=', gl_account),('company_id', '=', company.id)], limit=1).id
            else:
                income_account_id = res_config_obj.get_param('bs_register_payment_income_account_id', default=False)
                browse_income_account_id = self.env['account.account'].browse(int(income_account_id))
                if browse_income_account_id.company_id != company:
                    income_account_id = account_obj.search([('name', '=', browse_income_account_id.name), ('code', '=', browse_income_account_id.code),('company_id', '=', company.id)], limit=1).id

            if not income_account_id:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Income Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                               'rowline': ''}])

            if any(error_line_vals) and (context.get('validate') or context.get('account.payment.import')):
                self.env.cr.execute('''delete from importpayment_errorlines where importpayment_id=%s ''', (self.id,))
                self.exception = True
                _logger.info("Errors encountered.Payment cannot be initiated")
                self.errorline_ids = error_line_vals
                self.payment_file, self.payment_filename, self.state = '', '', 'exception'
                self.noexception = False
            else:
                self.env.cr.execute('''delete from importpayment_errorlines where importpayment_id=%s ''', (self.id,))
                self.noexception, self.exception, self.state = True, False, 'noexception'

            # return {
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'account.payment.import',
            #     'view_mode': 'form',
            #     'view_type': 'form',
            #     'res_id': self.id,
            #     'views': [(False, 'form')],
            #     'target': 'new',
            # }

            if ('Invoice Number' in values and values['Invoice Number']) or ('P/O Number' in values and values['P/O Number']):
                ###search invoice with TPH invoice number
                if 'Invoice Number' in values and values['Invoice Number']:
                    value_of_invoice_number = str(values['Invoice Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                elif 'P/O Number' in values and values['P/O Number']:
                    value_of_invoice_number = str(values['P/O Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                tph_invoice = self.get_tph_invoice(value_of_invoice_number.strip(), receivable_account_ids)
                if tph_invoice:
                    ##assuming we will got only one record for the  tph_invoice
                    account_move = account_move_line_obj.browse(tph_invoice)
                    if account_move.move_id:
                        invoice = account_move.move_id
                else:
                    if value_of_invoice_number.strip() not in invoice_data:
                        invoice_data[value_of_invoice_number.strip()] = {}
                        invoice_data[value_of_invoice_number.strip()]['partner'] = values['Partner']
                        invoice_data[value_of_invoice_number.strip()]['invoice_date'] = self.parse_date(values['Invoice Date'])
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] = self.validate_amountvalue(values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] = self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(values['Discount Amount'])
                        # invoice_data[value_of_invoice_number.strip()]['writeoff_amount'] = self.validate_amountvalue(values['WHT Amount'])
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'] = {}
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'][i] = {'ref': str(value_of_invoice_number), 'Partner': values['Partner'], 'invoice_date': self.parse_date(values['Invoice Date']), 'description': values['Invoice Description'], 'gross_amount': self.validate_amountvalue(values['Gross Amount']), 'income_account_id': income_account_id, 'analytic_distribution': analytic_distribution,'discount_amount':self.validate_amountvalue(values['Discount Amount']),'net_amount':self.validate_amountvalue(values['Net Amount'])}
                    else:
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] += self.validate_amountvalue(values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] = self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(values['Discount Amount'])
                        # invoice_data[value_of_invoice_number.strip()]['writeoff_amount'] = self.validate_amountvalue(values['WHT Amount'])
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'][i] = {'ref': str(value_of_invoice_number), 'Partner': values['Partner'], 'invoice_date': self.parse_date(values['Invoice Date']), 'description': values['Invoice Description'], 'gross_amount': self.validate_amountvalue(values['Gross Amount']), 'income_account_id': income_account_id, 'analytic_distribution': analytic_distribution,'discount_amount':self.validate_amountvalue(values['Discount Amount']),'net_amount':self.validate_amountvalue(values['Net Amount'])}

        inv_ids = self.get_invoice(value_of_invoice_number, invoice_data, dryrun)
        invoice = invoice_obj.browse(inv_ids)


        rownumber = 1
        for i in range(len(reader_info)):
            commercial_partner_id = False
            val = {}
            payment_vals = {}
            rownumber += 1
            field = reader_info[i]
            is_journal_entry = False
            sale_journal_entry = False
            invoice = False
            # values = dict(zip(keys, [field_val.strip() if type(field_val) == str else field_val for field_val in field]))
            values = dict(
                (key.strip(), field_val.strip() if type(field_val) == str else field_val) for key, field_val in
                zip(keys, field))

            if ('Invoice Number' in values and values['Invoice Number']) or ('P/O Number' in values and values['P/O Number']):
                ###search invoice with TPH invoice number
                if 'Invoice Number' in values and values['Invoice Number']:
                    value_of_invoice_number = str(values['Invoice Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                elif 'P/O Number' in values and values['P/O Number']:
                    value_of_invoice_number = str(values['P/O Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                # tph_invoice = account_move_line_obj.search([('tph_invoice_id', '=', value_of_invoice_number.strip()),
                #                                            ('account_id', 'in', receivable_account_ids)])
                tph_invoice = self.get_tph_invoice(value_of_invoice_number.strip(), receivable_account_ids)
                if tph_invoice:
                    ##assuming we will got only one record for the  tph_invoice
                    account_move = account_move_line_obj.browse(tph_invoice)
                    if account_move.move_id:
                        invoice = account_move.move_id
                    # elif account_move.move_id and not account_move.reconciled:
                    #     sale_journal_entry = account_move.move_id
                else:
                    # invoice = invoice_obj.search([('number', '=', value_of_invoice_number)
                    invoice_vals = {}
                    if self.is_new_invoice:
                        invoice_vals[value_of_invoice_number.strip()] = {}
                        invoice_vals[value_of_invoice_number.strip()] = {'ref': str(value_of_invoice_number), 'partner': values['Partner'], 'invoice_date': values['Invoice Date'], 'gross_amount': values['Gross Amount'],'income_account_id': income_account_id}
                    inv_ids = self.get_invoice(value_of_invoice_number, invoice_vals)
                    invoice = invoice_obj.browse(inv_ids)
                if invoice:
                    if invoice.payment_state == 'in_payment':
                        error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                       'comment': 'Invoice number %s already paid' % (
                                                           values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    elif invoice.state != 'posted' and not dryrun:
                        error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                       'comment': 'Invoice number %s is in %s state.\n' \
                                                                  'Invoice state should be: Posted' % (
                                                                      invoice.state, values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        # continue
                    else:
                        commercial_partner_id = invoice.commercial_partner_id

                if not invoice:
                    # Check if direct journal entry created
                    if not sale_journal_entry:
                        sale_journal_entry = self.get_sale_journal_entry(values['Invoice Number'])
                        if sale_journal_entry and not sale_journal_entry.partner_id:
                            error_line_vals.append([0, 0, {'importpayment_id': self.id,
                                                           'comment': 'Partner is missing in journal item for Invoice number %s.' \
                                                                      % (values['Invoice Number']),
                                                           'rowline': rownumber}])
                            continue
                        commercial_partner_id = sale_journal_entry and sale_journal_entry.partner_id and sale_journal_entry.partner_id.commercial_partner_id
                    if not sale_journal_entry:
                        error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                       'comment': 'Invoice Number %s not found' % (
                                                           values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    else:
                        is_journal_entry = True
                        commercial_partner_id = sale_journal_entry.partner_id

            else:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invoice number not found in csv sheet',
                                               'rowline': rownumber}])
                # continue

            if invoice and invoice.partner_id.name != values['Partner']:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Partner name not matching with invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])

            # date = datetime.strptime(values['Invoice Date'], "%m-%d-%Y").date()
            date = self.parse_date(values['Invoice Date'])
            if invoice and str(invoice.invoice_date) != date:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invoice date not matching for invoice %s' % (
                                                   invoice.ref), \
                                               'rowline': rownumber}])

                # CHECK GROSS AMOUNT
            if not values['Gross Amount'] or values['Gross Amount'] == '0':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Gross Amount not found in csv sheet for invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue
            gross_amount = self.validate_amountvalue(values['Gross Amount'])
            if not gross_amount:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invalid gross amount %s for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue

            if values['Gross Amount'] and float(self.validate_amountvalue(values['Gross Amount']))< 0 and float(self.validate_amountvalue(values['Net Amount'])) > 0:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invalid Net amount %s for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
            if is_journal_entry and receivable_account_ids:
                # self.env.cr.execute('''select COALESCE(sum(debit-credit), 0.0) from account_move_line where ''' \
                #                     '''move_id=%s and account_id in %s''', \
                #                     (sale_journal_entry.id, receivable_account_ids))
                # amount_total_signed = map(lambda x: x[0], self.env.cr.fetchall())
                amount_total_signed = self.get_signed_amount(sale_journal_entry, receivable_account_ids)
                if gross_amount != amount_total_signed[0]:
                    # flag_add_error = True
                    # Check one journal have positive and refund line.
                    # result_move_lines = self.check_move_lines(sale_journal_entry, receivable_account_ids)
                    # if result_move_lines and gross_amount in result_move_lines:
                    # flag_add_error = False
                    # if gross_amount > 0:
                    #     total_positive_amt = self.get_total_amount(sale_journal_entry, receivable_account_ids, 'positive')
                    # elif gross_amount < 0:
                    #     total_positive_amt = self.get_total_amount(sale_journal_entry, receivable_account_ids, 'negative')
                    # if flag_add_error:
                    #     error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                    #                                    'comment': 'Gross amount mismatch for invoice %s.\n' \
                    #                                               'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                    #                                               % (values['Invoice Number'], values['Gross Amount'],
                    #                                                  amount_total_signed), \
                    #                                    'rowline': rownumber}])
                    #     continue
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Gross amount mismatch for invoice %s.\n' \
                                                              'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                                                              % (values['Invoice Number'], values['Gross Amount'],
                                                                 amount_total_signed), \
                                                   'rowline': rownumber}])
                    # continue
            elif invoice and gross_amount != round(invoice.amount_total_signed, 2):
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Gross amount mismatch for invoice %s.\n' \
                                                          'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                                                          % (values['Invoice Number'], values['Gross Amount'],
                                                             invoice.amount_total_signed), \
                                               'rowline': rownumber}])
                # continue
            # CHECK NET AMOUNT
            if not values['Net Amount'] or values['Net Amount'] == '0':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Net Amount not found in csv sheet for invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue

            net_amount = self.validate_amountvalue(values['Net Amount'])
            if not net_amount:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invalid net amount %s found in csv sheet for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue

            # CHECK INVOICE TYPES
            if is_journal_entry:
                journal_type = sale_journal_entry.journal_id.type
                pay_type = 'inbound' if journal_type == 'sale' \
                    else 'outbound'
            elif invoice:
                invoice_type = invoice.move_type
                pay_type = 'inbound' if invoice_type in ['out_invoice', 'out_refund'] \
                    else 'outbound'
            if context.get('transaction_type') == 'inbound' and pay_type == 'outbound':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Vendor invoice %s cannot be imported from customer window' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue
            elif context.get('transaction_type') == 'outbound' and pay_type == 'inbound':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Customer invoice %s cannot be imported from Vendor window' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue
            else:
                pass

            # Check Discount Account
            if 'Discount Account' in values and values['Discount Account'] != '':
                discount_account = str(values['Discount Account'])
                discount_account = discount_account.split('.')[0]
                discount_account = discount_account.split(',')[0]
                discount_account_id = account_obj.search([('code', '=', discount_account), ('deprecated', '=' , False),('company_id', '=' , company.id)])
                if not discount_account_id:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Discount Account %s not found for invoice %s' % (discount_account, values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(discount_account_id) > 1:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Duplicate Discount Account %s found for invoice %s' % (discount_account,
                                                       values['Invoice Number']), \
                                                   'rowline': rownumber}])
            # Check Analytic Account
            if 'Analytic Account' in values and values['Analytic Account'] != '':
                analytic_account_id = analytic_account_obj.search(['|',('name', '=', values['Analytic Account']),('code', '=', values['Analytic Account']),('company_id', '=' , company.id)])
                if not analytic_account_id:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Analytic Account not found for invoice %s' % (values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(analytic_account_id) > 1:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Duplicate Analytic Account %s found' % (
                                                       values['Analytic Account']), \
                                                   'rowline': rownumber}])

                if 'Analytic Distribution' in values and not values['Analytic Distribution']:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Analytic Distribution %s found' % (
                                                       values['Analytic Distribution']), \
                                                   'rowline': rownumber}])

            if pay_type == 'outbound':
                if payment_method_id.id not in [payment_method.id for payment_method in
                                                   journal_id.outbound_payment_method_line_ids]:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Payment method type not found' \
                                                              'Journal/Payment method: %s\nPayment method type: %s' % (
                                                                  values['Payment Method'],
                                                                  values['Payment Method Type']), \
                                                   'rowline': rownumber}])
                    # continue

            # GET PARTNER TYPE.Ex-Customer or Vendor
            partner_type = 'customer' if pay_type == 'inbound' else 'supplier'
            today_date = datetime.now().strftime('%Y-%m-%d')
            # SETUP PAYMENT VALUES
            user = user_obj.browse(self._uid)
            user_warehouse = user.property_warehouse_id.id if user.property_warehouse_id else False
            warehouse = False
            currency_id = False
            if is_journal_entry:
                # warehouse = sale_journal_entry.warehouse_id.id
                currency_id = sale_journal_entry.currency_id.id or \
                              user.company_id.currency_id.id
                if user_warehouse:
                    warehouse = user_warehouse
            else:
                # warehouse = invoice.warehouse_id.id
                if invoice:
                    currency_id = invoice.currency_id.id
                    if user_warehouse:
                        warehouse = user_warehouse

            payment_vals = {'payment_date': today_date, \
                            'communication': 'Payment created from csv sheet', \
                            'payment_difference_handling': 'open', 'journal_id': journal_id[0].id, \
                            'warehouse_id': warehouse, \
                            'currency_id': currency_id, u'partner_type': partner_type, \
                            'amount': net_amount, 'writeoff_account_id': False, \
                            'payment_type': pay_type, 'payment_method_line_id': self.payment_method_line_id.id, \
                            'invoice': invoice,
                            'is_journal_entry': is_journal_entry

                            }
            if commercial_partner_id:
                payment_vals.update({'partner_id': commercial_partner_id.id})
            # GET RECEIVABLE MOVE LINE
            if self.noexception:
                move_id = sale_journal_entry if is_journal_entry else invoice
                # move_line = [line.id for line in move_id.line_ids \
                #              if line.account_id.user_type_id.name in
                #              ["Receivable", "Payable"]]
                move_line = []
                if move_id and account_ids:
                    self._cr.execute('''SELECT id FROM account_move_line
                                                    WHERE move_id = %s AND account_id in (%s)
                                                    AND reconciled = False ORDER BY date_maturity
                                                ''' % (move_id.id, ','.join(map(str, account_ids))))
                    move_line = [mv_ln[0] for mv_ln in self._cr.fetchall()]
                # payment_vals.update({'line_ids': move_line})
                register_payment_obj = register_payment_obj.with_context( \
                    uid=self.env.uid, active_model='account.move.line', \
                    search_disable_custom_filters=True, active_ids=move_line, \
                    active_id=move_line[0] if move_line else False)

                    # continue
                # if payment_vals.get('communication') and commercial_partner_id:
                #     is_allow_check = self.allow_check_number(payment_vals.get('communication'), commercial_partner_id.id)
                #     if not is_allow_check:
                #         error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                #                                        'comment': 'You have already use same check number for another partner.\n' \
                #                                                   'Check number is %s.'
                #                                                   % (values['Check Number']),
                #                                        'rowline': rownumber}])
                        # continue

            # PAYMENT VIA DISCOUNT
            if values['Discount Amount'] and values['Discount Amount'] and not self.validate_amountvalue(values['Discount Amount']) == 0.0:
                if not self.validate_amountvalue(values['Discount Amount']):
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Invalid discount amount %s found for invoice %s.' \
                                                              % (values['Discount Amount'], values['Invoice Number']),
                                                   'rowline': rownumber}])

                if values['Gross Amount'] and float(self.validate_amountvalue(values['Gross Amount']))< 0:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'You can not give discount on credit note please remove discount amount %s found for  %s.' \
                                                              % (values['Discount Amount'], values['Invoice Number']),
                                                   'rowline': rownumber}])
                    # continue
                payment_vals = self.pay_discount(payment_vals, values)

            if 'Discount Amount' in values and values['Discount Amount'] != '' and self.validate_amountvalue(values['Discount Amount']) != 0 and 'Discount Account' in values and values['Discount Account'] == '':
                discount_account = str(values['Discount Account'])
                discount_account = discount_account.split('.')[0]
                discount_account = discount_account.split(',')[0]
                discount_account_id = account_obj.search([('code', '=', discount_account), ('deprecated', '=', False),('company_id', '=' , company.id)])
                if not discount_account_id:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Discount Account not found for invoice %s' % (
                                                   values['Invoice Number']), \
                                                   'rowline': rownumber}])


            # if values['Discount Amount'] and float(values['Discount Amount']) > 0 and values['WHT Amount'] and float(values['WHT Amount']) > 0:
            #     error_line_vals.append([0, 0, {'importpayment_id': self.id, \
            #                                    'comment': 'Discount amount and WHT amount both can not be used together for invoice %s.' \
            #                                               % (values['Invoice Number']),
            #                                    'rowline': rownumber}])


            # For (Gross Amount - Net Amount) is less than or equal to 0.01.
            gross_amt = float(self.validate_amountvalue(values['Gross Amount'])) if values['Gross Amount'] else 0.0
            disc_amt = float(self.validate_amountvalue(values['Discount Amount'])) if values['Discount Amount'] else 0.0
            net_amt = float(self.validate_amountvalue(values['Net Amount'])) if values['Net Amount'] else 0.0

            # if net_amt < 0:
            #     error_line_vals.append([0, 0, {'importpayment_id': self.id, \
            #                                    'comment': 'Net Amount can not be less than Zero for invoice %s' \
            #                                               % (values['Invoice Number']),
            #                                    'rowline': rownumber}])

            diff_amt = float(str(gross_amt - disc_amt - net_amount))
            total_act_amt = disc_amt + net_amt
            if abs(gross_amt) >= abs(total_act_amt):
                if abs(diff_amt) <= 0.01:
                    disc_amt += diff_amt
                    values['Discount Amount'] = disc_amt
                    payment_vals = self.pay_discount(payment_vals, values)

            # Check (Dicount + Net Amount) not more than Gross Amount.
            total_pay_amt = round(payment_vals.get('amount') + payment_vals.get('payment_term_discount', 0.0), 2)
            if gross_amount > 0 and gross_amount < total_pay_amt:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'You cannot over pay against an invoice %s.' \
                                                          % (values['Invoice Number']),
                                               'rowline': rownumber}])

            ##updaate ammount_to_pay for the account move line based on the amount for the invoices and appleied discount to it
            # amount_to_pay = net_amount
            # if self.noexception:
            #     if payment_vals.has_key('payment_term_discount'):
            #         disc_to_pay = payment_vals['payment_term_discount']
            #
            #         # amount_to_pay+=payment_vals['payment_term_discount']
            #         self.env.cr.execute(
            #             'update account_move_line set actual_amount_to_pay = %s, discount_to_pay = %s where id = %s',
            #             (amount_to_pay, disc_to_pay, payment_vals['line_ids'][0]))
            #     else:
            #         self.env.cr.execute('update account_move_line set actual_amount_to_pay = %s where id = %s',
            #                             (amount_to_pay, payment_vals['line_ids'][0]))
            # payment_vals.update({'amount': net_amount})
            payment_list.append(payment_vals)

            # import  ipdb;ipdb.set_trace()
            # DISPLAY ERRORS


        if dryrun:
            self._cr.execute('ROLLBACK TO SAVEPOINT paymentimport')
            # cancel all changes done to the registry/ormcache
            self.pool.clear_caches()
            self.pool.reset_changes()
        else:
            self._cr.execute('RELEASE SAVEPOINT paymentimport')

        return error_line_vals



    def action_make_payment_button(self):
        self.action_import_payment(dryrun=False)
        self.action_make_payment()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_payments')
        # action['domain'] = [('id', 'in', payment.ids)]
        return action

    def action_make_payment(self):
        context = self.env.context
        invoice_obj = self.env['account.move']
        payment_obj = self.env['account.payment']
        journal_obj = self.env['account.journal']
        account_obj = self.env['account.account']
        analytic_account_obj = self.env['account.analytic.account']
        user_obj = self.env['res.users']
        payment_method_obj = self.env['account.payment.method.line']
        register_payment_obj = self.env['account.payment.register']
        partner_obj = self.env['res.partner']
        account_move_line_obj = self.env['account.move.line']
        error_line_vals = []
        invoices_ids = []
        journal_entry_ids = []
        payment_list = []
        used_discount_move_lst = []
        rownumber = 1
        pay_type = 'inbound'
        company = self.env.user.company_id
        if not self.payment_file:
            raise exceptions.ValidationError(_("You need to select a file!"))
        # DECODE THE FILE DATA
        if self.import_option == 'csv':
            reader_info,keys = self.get_csv_file_data()
        else:
            reader_info,keys = self.get_excel_file_data()
        # data = base64.b64decode(self.payment_file)
        # file_input = StringIO(data.decode("utf-8"))
        # file_input.seek(0)
        # reader_info = []
        # if self.delimeter:
        #     delimeter = str(self.delimeter)
        # else:
        #     delimeter = ','
        # reader = csv.reader(file_input, delimiter=delimeter, lineterminator='\r\n')
        # try:
        #     reader_info.extend(reader)
        # except Exception:
        #     raise exceptions.ValidationError(_("Not a valid file!"))
        # keys = reader_info[0]
        # # CHECK IF KEYS EXIST
        # if not isinstance(keys, list):
        #     raise exceptions.ValidationError(_("%s\nColumns not found in sheet") % ', '.join(csv_columns))
        # keys_not_exist = filter(lambda x: x not in csv_columns, keys)
        # if any(keys_not_exist):
        #     raise exceptions.ValidationError(
        #         _("%s\nColumns not found in sheet") % ', '.join(keys_not_exist))
        # del reader_info[0]
        values = {}
        # receivable_account_ids = tuple([account.id for account in self.env["account.account"].sudo().search(
        #     [("user_type_id", "=", "Receivable")])])
        self._cr.execute('''SELECT id FROM account_account WHERE account_type IN ('asset_receivable', 'liability_payable')''')
        account_ids = [accounts[0] for accounts in self._cr.fetchall()]
        receivable_account_ids = tuple(account_ids)

        res_config_obj = self.env['ir.config_parameter'].sudo()

        discount_account_id = res_config_obj.get_param('bs_register_payment_discount_account_id', default=False)
        browse_discount_account_id = self.env['account.account'].browse(int(discount_account_id))
        if browse_discount_account_id.company_id != company:
            discount_account_id = account_obj.search( [('name', '=', browse_discount_account_id.name), ('code', '=', browse_discount_account_id.code),('company_id', '=', company.id)], limit=1).id

        writeoff_account_id = res_config_obj.get_param('bs_register_payment_discount_account_id', default=False)
        browse_writeoff_account_id = self.env['account.account'].browse(int(writeoff_account_id))
        if browse_writeoff_account_id.company_id != company:
            writeoff_account_id = account_obj.search([('name', '=', browse_writeoff_account_id.name), ('code', '=', browse_writeoff_account_id.code),('company_id', '=', company.id)], limit=1).id

        income_account_id = res_config_obj.get_param('bs_register_payment_income_account_id', default=False)
        browse_income_account_id = self.env['account.account'].browse(int(income_account_id))
        if browse_income_account_id.company_id != company:
            income_account_id = account_obj.search([('name', '=', browse_income_account_id.name), ('code', '=', browse_income_account_id.code),('company_id', '=', company.id)], limit=1).id

        payment_method_id = self.payment_method_line_id
        journal_id = self.journal_id

        if not discount_account_id:
            error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                           'comment': 'Discount Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                           'rowline': ''}])

        if not writeoff_account_id:
            error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                           'comment': 'Write Off Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                           'rowline': ''}])

        if not income_account_id:
            error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                           'comment': 'Income Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                           'rowline': ''}])

        # """Create not exist invoice with multiple lines"""
        invoice_data = {}
        payment_amount = 0
        for i in range(len(reader_info)):
            commercial_partner_id = False
            val = {}
            payment_vals = {}
            field = reader_info[i]
            is_journal_entry = False
            sale_journal_entry = False
            invoice = False
            # values = dict(zip(keys, [field_val.strip() if type(field_val) == str else field_val for field_val in field]))

            values = dict(
                (key.strip(), field_val.strip() if type(field_val) == str else field_val) for key, field_val in
                zip(keys, field))
            # Check Analytic Account
            analytic_distribution = {}
            if 'Analytic Account' in values and values['Analytic Account'] != '':
                analytic_account_id = analytic_account_obj.search(['|',('name', '=', values['Analytic Account']),('code', '=', values['Analytic Account']),('company_id', '=' , company.id)])
                if not analytic_account_id:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Analytic Account %s not found for invoice %s' % (
                                                       values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(analytic_account_id) > 1:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Duplicate Analytic Account %s found for invoice %s' % (
                                                       values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])

                if 'Analytic Distribution' in values and not values['Analytic Distribution']:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id,
                                                   'comment': 'Analytic Distribution %s found for invoice %s' % (
                                                       values['Analytic Distribution'], values['Invoice Number']),
                                                   'rowline': rownumber}])

                analytic_distribution = {analytic_account_id.id: 100}

            if ('Invoice Number' in values and values['Invoice Number']) or ('P/O Number' in values and values['P/O Number']):
                ###search invoice with TPH invoice number
                if 'Invoice Number' in values and values['Invoice Number']:
                    value_of_invoice_number = str(values['Invoice Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                elif 'P/O Number' in values and values['P/O Number']:
                    value_of_invoice_number = str(values['P/O Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]

                tph_invoice = self.get_tph_invoice(value_of_invoice_number.strip(), receivable_account_ids)
                if tph_invoice:
                    ##assuming we will got only one record for the  tph_invoice
                    account_move = account_move_line_obj.browse(tph_invoice)
                    if account_move.move_id:
                        invoice = account_move.move_id
                    if value_of_invoice_number.strip() not in invoice_data:
                        invoice_data[value_of_invoice_number.strip()] = {}
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] = self.validate_amountvalue(
                            values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] = self.validate_amountvalue(
                            values['Net Amount'])
                        payment_amount += self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(
                            values['Discount Amount'])
                    else:
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] = self.validate_amountvalue(
                            values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] = self.validate_amountvalue(
                            values['Net Amount'])
                        payment_amount += self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(
                            values['Discount Amount'])
                else:
                    if value_of_invoice_number.strip() not in invoice_data:
                        invoice_data[value_of_invoice_number.strip()] = {}
                        invoice_data[value_of_invoice_number.strip()]['partner'] = values['Partner']
                        invoice_data[value_of_invoice_number.strip()]['invoice_date'] = self.parse_date(
                            values['Invoice Date'])
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] = self.validate_amountvalue(
                            values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] = self.validate_amountvalue(
                            values['Net Amount'])
                        payment_amount += self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(
                            values['Discount Amount'])
                        # invoice_data[value_of_invoice_number.strip()]['writeoff_amount'] = self.validate_amountvalue(values['WHT Amount'])
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'] = {}
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'][i] = {
                            'ref': str(value_of_invoice_number), 'Partner': values['Partner'],
                            'invoice_date': self.parse_date(values['Invoice Date']),
                            'description': values['Invoice Description'],
                            'gross_amount': self.validate_amountvalue(values['Gross Amount']),
                            'income_account_id': income_account_id, 'analytic_distribution': analytic_distribution}
                    else:
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] += self.validate_amountvalue(
                            values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] += self.validate_amountvalue(
                            values['Net Amount'])
                        payment_amount += self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(
                            values['Discount Amount'])
                        # invoice_data[value_of_invoice_number.strip()]['writeoff_amount'] = self.validate_amountvalue(values['WHT Amount'])
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'][i] = {
                            'ref': str(value_of_invoice_number), 'Partner': values['Partner'],
                            'invoice_date': self.parse_date(values['Invoice Date']),
                            'description': values['Invoice Description'],
                            'gross_amount': self.validate_amountvalue(values['Gross Amount']),
                            'income_account_id': income_account_id, 'analytic_distribution': analytic_distribution}

        inv_ids = self.get_invoice(value_of_invoice_number, invoice_data)

        invoice = invoice_obj.browse(inv_ids)
        all_invoices = invoice.filtered(lambda i: i.move_type == 'out_invoice').ids
        payment_invoice_ids = []
        outstanding_invoice_ids = []

        payment = payment_obj.sudo().create({
            'amount': payment_amount,
            'partner_type': 'customer',
            'partner_id': invoice[0].partner_id.id,
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'check_number': self.check_number,
            'date': self.payment_date,
            'ref': self.communication,
        })
        payment.action_post()
        for i in range(len(reader_info)):
            commercial_partner_id = False
            val = {}
            payment_vals = {}
            rownumber += 1
            field = reader_info[i]
            is_journal_entry = False
            sale_journal_entry = False
            invoice = False

            # values = dict(zip(keys, [field_val.strip() if type(field_val) == str else field_val for field_val in field]))
            values = dict(
                (key.strip(), field_val.strip() if type(field_val) == str else field_val) for key, field_val in
                zip(keys, field))
            # GET INVOICE RECORD
            if ('Invoice Number' in values and values['Invoice Number']) or ('P/O Number' in values and values['P/O Number']):
                ###search invoice with TPH invoice number
                if 'Invoice Number' in values and values['Invoice Number']:
                    value_of_invoice_number = str(values['Invoice Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                elif 'P/O Number' in values and values['P/O Number']:
                    value_of_invoice_number = str(values['P/O Number'])
                    value_of_invoice_number = value_of_invoice_number.split('.')[0]
                    value_of_invoice_number = value_of_invoice_number.split(',')[0]
                # tph_invoice = account_move_line_obj.search(
                #    [('tph_invoice_id', '=', tph_invoice_number.strip()), ('account_id', 'in', receivable_account_ids)])
                tph_invoice = self.get_tph_invoice(value_of_invoice_number.strip(), receivable_account_ids)
                if tph_invoice:
                    ##assuming we will got only one record for the  tph_invoice
                    account_move = account_move_line_obj.browse(tph_invoice)
                    if account_move.move_id:
                        invoice = account_move.move_id
                    # elif account_move.move_id and not account_move.reconciled:
                    #     sale_journal_entry = account_move.move_id
                else:
                    # invoice = invoice_obj.search([('number', '=', values['Invoice Number'])])
                    inv_ids = self.get_invoice(value_of_invoice_number)
                    invoice = invoice_obj.browse(inv_ids)

                if invoice:
                    if invoice.payment_state == 'in_payment':
                        error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                       'comment': 'Invoice number %s already paid' % (
                                                           values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    elif invoice.state != 'posted':
                        error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                       'comment': 'Invoice number %s is in %s state.\n' \
                                                                  'Invoice state should be: Posted' % (
                                                                      invoice.state, values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    commercial_partner_id = invoice.commercial_partner_id

                if not invoice:
                    # Check if direct journal entry created
                    if not sale_journal_entry:
                        sale_journal_entry = self.get_sale_journal_entry(values['Invoice Number'])
                        if sale_journal_entry and not sale_journal_entry.partner_id:
                            error_line_vals.append([0, 0, {'importpayment_id': self.id,
                                                           'comment': 'Partner is missing in journal item for Invoice number %s.' \
                                                                      % (values['Invoice Number']),
                                                           'rowline': rownumber}])
                            continue
                        commercial_partner_id = sale_journal_entry and sale_journal_entry.partner_id and sale_journal_entry.partner_id.commercial_partner_id
                    if not sale_journal_entry:
                        error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                       'comment': 'Invoice Number %s not found' % (
                                                           values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    else:
                        is_journal_entry = True
                        commercial_partner_id = sale_journal_entry.partner_id

            else:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invoice number not found in csv sheet',
                                               'rowline': rownumber}])
                continue

            # CHECK GROSS AMOUNT
            if not values['Gross Amount'] or values['Gross Amount'] == '0':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Gross Amount not found in csv sheet for invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                continue

            gross_amount = self.validate_amountvalue(values['Gross Amount'])
            if not gross_amount:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invalid gross amount %s for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
                continue
            if is_journal_entry and receivable_account_ids:
                # self.env.cr.execute('''select COALESCE(sum(debit-credit),0.0) from account_move_line where ''' \
                #                     '''move_id=%s and account_id in %s''', \
                #                     (sale_journal_entry.id, receivable_account_ids))
                # amount_total_signed = map(lambda x: x[0], self.env.cr.fetchall())
                amount_total_signed = self.get_signed_amount(sale_journal_entry, receivable_account_ids)
                if gross_amount != round(amount_total_signed[0], 2):
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Gross amount mismatch for invoice %s.\n' \
                                                              'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                                                              % (values['Invoice Number'], values['Gross Amount'],
                                                                 amount_total_signed), \
                                                   'rowline': rownumber}])
                    continue
            elif gross_amount != round(invoice.amount_total_signed, 2):
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Gross amount mismatch for invoice %s.\n' \
                                                          'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                                                          % (values['Invoice Number'], values['Gross Amount'],
                                                             invoice.amount_total_signed), \
                                               'rowline': rownumber}])
                continue
            # CHECK NET AMOUNT
            if not values['Net Amount'] or values['Net Amount'] == '0':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Net Amount not found in csv sheet for invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                continue

            net_amount = self.validate_amountvalue(values['Net Amount'])
            if not net_amount:
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Invalid net amount %s found in csv sheet for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
                continue

            # CHECK INVOICE TYPES
            if is_journal_entry:
                journal_type = sale_journal_entry.journal_id.type
                pay_type = 'inbound' if journal_type == 'sale' \
                    else 'outbound'
            else:
                invoice_type = invoice.move_type
                pay_type = 'outbound'
                pay_type = 'inbound' if invoice_type in ['out_invoice', 'out_refund'] \
                    else 'outbound'

            if context.get('transaction_type') == 'inbound' and pay_type == 'outbound':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Vendor invoice %s cannot be imported from customer window' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                continue
            elif context.get('transaction_type') == 'outbound' and pay_type == 'inbound':
                error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                               'comment': 'Customer invoice %s cannot be imported from Vendor window' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                continue
            else:
                pass

            if pay_type == 'outbound':
                if payment_method_id.id not in [payment_method.id for payment_method in
                                                   journal_id.outbound_payment_method_line_ids]:
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Payment method type not found' \
                                                              'Journal/Payment method: %s\nPayment method type: %s' % (
                                                                  values['Payment Method'],
                                                                  values['Payment Method Type']), \
                                                   'rowline': rownumber}])
                    continue

            # GET PARTNER TYPE.Ex-Customer or Vendor
            partner_type = 'customer' if pay_type == 'inbound' else 'supplier'
            today_date = datetime.now().strftime('%Y-%m-%d')
            # SETUP PAYMENT VALUES
            user = user_obj.browse(self._uid)
            warehouse = False
            currency_id = False
            user_warehouse = user.property_warehouse_id.id if user.property_warehouse_id else False
            if is_journal_entry:
                warehouse = sale_journal_entry.warehouse_id.id
                currency_id = sale_journal_entry.currency_id.id or user.company_id.currency_id.id
                if user_warehouse:
                    warehouse = user_warehouse
            else:
                # warehouse = invoice.warehouse_id.id
                currency_id = invoice.currency_id.id
                if user_warehouse:
                    warehouse = user_warehouse
            payment_difference_handling = 'open'
            writeoff_account_id = False
            writeoff_label = 'Write-Off'
            res_config_obj = self.env['ir.config_parameter'].sudo()
            payment_difference = 0
            deduction_ids = []
            if 'Discount Amount' in values and values['Discount Amount'] and float(self.validate_amountvalue(values['Discount Amount'])) != 0:
                payment_difference_handling = 'reconcile'
                payment_difference = float(self.validate_amountvalue(values['Discount Amount']))
                writeoff_label = 'Discount'
                # discount_account_id = res_config_obj.get_param('bs_register_payment_discount_account_id', default=False)
                discount_account = str(values['Discount Account'])
                discount_account = discount_account.split('.')[0]
                discount_account = discount_account.split(',')[0]
                discount_account_id = account_obj.search([('code', '=', discount_account), ('deprecated', '=', False),('company_id', '=' , company.id)]).id
                writeoff_label = 'Discount' #+ str(discount_account_id)
                deduction_ids.append((0, 0, {'name': writeoff_label, 'amount_currency': payment_difference,'account_id': int(discount_account_id), 'analytic_account_id': False}))
            # if 'WHT Amount' in values and values['WHT Amount'] and float(self.validate_amountvalue(values['WHT Amount'])) > 0:
            #     payment_difference_handling = 'reconcile'
            #     payment_difference = float(self.validate_amountvalue(values['WHT Amount']))
            #     writeoff_label = 'Write-Off'
            #     writeoff_account_id = res_config_obj.get_param('bs_register_payment_writeoff_account_id', default=False)
            #     deduction_ids.append((0, 0,{'name': writeoff_label, 'amount': payment_difference, 'account_id': int(writeoff_account_id), 'analytic_account_id': False, 'analytic_tag_ids': False}))

            if len(deduction_ids) > 0:
                payment_difference_handling = 'reconcile_multi_deduct'

                payment_vals = {
                    'payment_date': today_date,
                    'communication': 'Payment created from csv sheet',
                    'payment_difference_handling': payment_difference_handling,
                    'journal_id': self.journal_id.id,
                    'payment_method_line_id': self.payment_method_line_id.id,
                    'currency_id': currency_id,
                    'partner_type': partner_type,
                    'amount': net_amount,
                    'deduction_ids': deduction_ids,
                    'payment_type': pay_type,
                    'writeoff_label': writeoff_label,
                    'communication': self.communication,
                    'check_number': self.check_number,
                }
                if invoice.move_type == 'out_invoice':
                    common_allocation = self.env['common.allocation'].create({
                        'reference': invoice.name,
                        # 'invoice_line_id': payment_invoice.id,
                        'invoice_id': invoice.id,
                        # 'date': payment_invoice.payment_date,
                        'total_amount': self.validate_amountvalue(values['Gross Amount']),
                        'amount_residual': self.validate_amountvalue(values['Gross Amount']),
                        'allocation': self.validate_amountvalue(values['Net Amount']),
                        'discount_amount': payment_difference,
                        # 'amount_allowed_discount': line.amount_allowed_discount,
                        # 'sale_tax': line.sale_tax,
                        # 'payment_difference': line.payment_difference,
                        # 'select_all': line.select_all,
                        'is_outstanding_line': False,
                        'linked_payment_id': payment.id,
                        # 'move_line_ids': [(6, 0, line.move_line_ids.ids)],
                        # 'state': line.state,
                        'select': True,
                        'select_all': True,
                        'discount_account_id': discount_account_id,

                    })
                else:
                    common_allocation = self.env['common.allocation'].create({
                        'reference': invoice.name,
                        'date': invoice.date,
                        'amount_residual': self.validate_amountvalue(values['Gross Amount']),
                        'allocation': self.validate_amountvalue(values['Net Amount']),
                        'is_outstanding_line': True,
                        'linked_payment_id': payment.id,
                        'select': True,
                        # 'select_all': True,
                    })
                    common_allocation_update = self.env['common.allocation'].search(['|',('reference','=',invoice.ref),('reference','=',invoice.name)])
                    if common_allocation_update:
                        common_allocation_update.sudo().write({'select': True})
                if invoice.ref in invoice_data:
                    invoice_data[invoice.ref]['common_allocation_id'] = common_allocation.id
                else:
                    invoice_data[invoice.name]['common_allocation_id'] = common_allocation.id

                continue
            else:
                if invoice.move_type == 'out_invoice':
                    common_allocation = self.env['common.allocation'].create({
                        'reference': invoice.name,
                        # 'invoice_line_id': payment_invoice.id,
                        'invoice_id': invoice.id,
                        # 'date': payment_invoice.payment_date,
                        'total_amount': self.validate_amountvalue(values['Gross Amount']),
                        'amount_residual': self.validate_amountvalue(values['Gross Amount']),
                        'allocation': self.validate_amountvalue(values['Net Amount']),
                        'discount_amount': payment_difference,
                        # 'amount_allowed_discount': line.amount_allowed_discount,
                        # 'sale_tax': line.sale_tax,
                        # 'payment_difference': line.payment_difference,
                        # 'select_all': line.select_all,
                        'is_outstanding_line': False,
                        'linked_payment_id': payment.id,
                        # 'move_line_ids': [(6, 0, line.move_line_ids.ids)],
                        # 'state': line.state,
                        'select': True,
                        'select_all': False,
                        'discount_account_id': discount_account_id,
                    })
                else:
                    common_allocation = self.env['common.allocation'].create({
                        'reference': invoice.name,
                        'date': invoice.date,
                        'amount_residual': self.validate_amountvalue(values['Gross Amount']),
                        'allocation': self.validate_amountvalue(values['Net Amount']),
                        'is_outstanding_line': True,
                        'linked_payment_id': payment.id,
                        'select': True,
                        # 'select_all': True,
                    })
                    common_allocation_update = self.env['common.allocation'].search(['|', ('reference', '=', invoice.ref), ('reference', '=', invoice.name)])
                    if common_allocation_update:
                        common_allocation_update.sudo().write({'select': True})
                if invoice.ref in invoice_data:
                    invoice_data[invoice.ref]['common_allocation_id'] = common_allocation.id
                else:
                    invoice_data[invoice.name]['common_allocation_id'] = common_allocation.id

                continue
                payment_vals = {
                    'payment_date': today_date,
                        'communication': 'Payment created from csv sheet',
                        'payment_difference_handling': payment_difference_handling,
                        'journal_id': self.journal_id.id,
                        'payment_method_line_id': self.payment_method_line_id.id,
                        'currency_id': currency_id,
                        'partner_type': partner_type,
                        'amount': net_amount,
                        'writeoff_account_id': int(writeoff_account_id) if writeoff_account_id else False,
                        'payment_type': pay_type,
                        'writeoff_label': writeoff_label,
                        'deduction_ids': [],
                        'communication': self.communication,
                        'check_number': self.check_number,
                    }
            if commercial_partner_id:
                payment_vals.update({'partner_id': commercial_partner_id.id})
            # GET RECEIVABLE MOVE LINE
            if self.noexception:
                move_id = sale_journal_entry if is_journal_entry else invoice.id
                # move_line = [line.id for line in move_id.line_ids \
                #              if line.account_id.user_type_id.name in ["Receivable", "Payable"] \
                #              and not line.reconciled]
                move_line = []
                if move_id and account_ids:
                    self._cr.execute('''SELECT id FROM account_move_line
                                                WHERE move_id = %s AND account_id in (%s)
                                                AND reconciled = False ORDER BY date_maturity
                                            ''' % (move_id, ','.join(map(str, account_ids))))
                    move_line = [mv_ln[0] for mv_ln in self._cr.fetchall()]
                payment_vals.update({'line_ids': move_line})

                register_payment_obj = register_payment_obj.with_context( \
                    uid=self.env.uid, active_model='account.move.line', \
                    search_disable_custom_filters=True, active_ids=move_line, \
                    active_id=move_line[0] if move_line else False)

            if not payment_vals.get('communication'):
                payment_vals.update({'communication': 0})
            # PAYMENT VIA DISCOUNT
            if values['Discount Amount'] and not self.validate_amountvalue(values['Discount Amount']) == 0.0:
                if not self.validate_amountvalue(values['Discount Amount']):
                    error_line_vals.append([0, 0, {'importpayment_id': self.id, \
                                                   'comment': 'Invalid discount amount %s found for invoice %s.' \
                                                              % (values['Discount Amount'], values['Invoice Number']),
                                                   'rowline': rownumber}])
                    continue
                payment_vals = self.pay_discount(payment_vals, values)

            # For (Gross Amount - Net Amount) is less than or equal to 0.01.
            gross_amt = float(self.validate_amountvalue(values['Gross Amount'])) if values['Gross Amount'] else 0.0
            disc_amt = float(self.validate_amountvalue(values['Discount Amount'])) if values['Discount Amount'] else 0.0
            net_amt = float(self.validate_amountvalue(values['Net Amount'])) if values['Net Amount'] else 0.0

            diff_amt = float(gross_amt - disc_amt - net_amount)
            total_act_amt = disc_amt + net_amt
            if abs(gross_amt) >= abs(total_act_amt):
                if abs(diff_amt) and abs(diff_amt) <= 0.01:
                    disc_amt += diff_amt
                    values['Discount Amount'] = disc_amt
                    payment_vals = self.pay_discount(payment_vals, values)

            ##updaate ammount_to_pay for the account move line based on the amount for the invoices and appleied discount to it
            amount_to_pay = net_amount
            if self.noexception and payment_vals.get('line_ids'):
                mv_line_lst = payment_vals['line_ids']
                if payment_vals.get('payment_term_discount'):
                    disc_to_pay = payment_vals['payment_term_discount']
                    self.env.cr.execute('''SELECT id FROM account_move_line 
                                                    WHERE id IN (%s) LIMIT 1
                                                ''' % (','.join(map(str, mv_line_lst))))
                    line_datas = self.env.cr.fetchone()
                    if line_datas:
                        # self.env.cr.execute('''UPDATE account_move_line
                        #                                 SET actual_amount_to_pay=signed_amount_residual - %s, discount_to_pay = %s,
                        #                                 difference_amount=0.0, is_used_discount = True
                        #                                 WHERE id = %s
                        #                             ''' % (disc_to_pay, disc_to_pay, line_datas[0]))
                        used_discount_move_lst.append(line_datas[0])
                        if len(mv_line_lst) > 1:
                            update_move_line_lst = list(set(mv_line_lst) - set([line_datas[0]]))
                            # self.env.cr.execute('''UPDATE account_move_line
                            #                                 SET actual_amount_to_pay=signed_amount_residual, discount_to_pay=0.0,
                            #                                 difference_amount=0.0
                            #                                 WHERE id in (%s) AND (is_used_discount = False OR is_used_discount IS NULL)
                            #                             ''' % (','.join(map(str, update_move_line_lst))))
                # else:
                    ## self.env.cr.execute('update account_move_line set actual_amount_to_pay = %s where id = %s',(amount_to_pay,payment_vals['line_ids'][0]))
                    # self.env.cr.execute('''UPDATE account_move_line
                    #                                 SET actual_amount_to_pay=signed_amount_residual, discount_to_pay=0.0,
                    #                                 difference_amount=0.0, is_used_discount=False
                    #                                 WHERE id IN (%s) AND (discount_to_pay != 0.0 OR difference_amount != 0.0)
                    #                             ''' % (','.join(map(str, mv_line_lst))))
                    # AND is_used_discount = False
            payment_list.append(payment_vals)

        common_allocation = self.env['common.allocation'].create({
            'reference': payment.name,
            # 'invoice_line_id': payment_invoice.id,
            # 'invoice_id': invoice.id,
            'date': payment.date,
            # 'total_amount': values['Gross Amount'],
            'amount_residual': payment.amount,
            'allocation': payment.amount,
            # 'amount_allowed_discount': line.amount_allowed_discount,
            # 'sale_tax': line.sale_tax,
            # 'payment_difference': line.payment_difference,
            # 'select_all': line.select_all,
            'is_outstanding_line': True,
            'linked_payment_id': payment.id,
            # 'move_line_ids': [(6, 0, line.move_line_ids.ids)],
            # 'state': line.state,
            'select': True,
            # 'select_all': True,
        })

        payment.prepare_invoice_lines()
        payment.add_previous_outstanding_payment()
        payment.invoice_lines = payment.invoice_lines.filtered(lambda i:i.invoice_id.id in all_invoices)
        i = 0
        for payment_line in payment.invoice_lines:
            if payment_line.invoice_id.ref in invoice_data:
                reference_link = payment_line.invoice_id.ref
            else:
                reference_link = payment_line.invoice_id.name

            select_all = True if (invoice_data[reference_link]['discount_amount'] + invoice_data[reference_link]['net_amount']) == invoice_data[reference_link]['gross_amount'] else False
            payment_line.write({
                'discount_amount': invoice_data[reference_link]['discount_amount'],
                'allocation': invoice_data[reference_link]['net_amount'] ,
                'common_allocation_id': invoice_data[reference_link]['common_allocation_id'],
                'select': True,
                'select_all': select_all
            })
            payment_line._get_payment_difference()

        common_ids = self.env['common.allocation'].search([('linked_payment_id', '=', payment.id)])
        for outstanding_id in payment.outstanding_payment_ids:
            if outstanding_id.reference in invoice_data or outstanding_id.move_id.ref in invoice_data:
                outstanding_id.write({
                    'amount_to_utilize': invoice_data[outstanding_id.reference]['net_amount'] if outstanding_id.reference in invoice_data else invoice_data[outstanding_id.move_id.ref]['net_amount'],
                })

            common_id = self.env['common.allocation'].search([('outstanding_line_id', '=', outstanding_id.id)])
            if common_id:
                continue
            is_payment_line = False
            amount_residual = 0
            if outstanding_id.move_payment_id.id == payment.id:
                is_payment_line = True
                amount_residual = outstanding_id.amount_residual

            common_vals = {
                'linked_payment_id': payment.id,
                'move_id': outstanding_id.move_id.id,
                'reference': outstanding_id.move_id.name or outstanding_id.move_payment_id.name,
                'outstanding_line_id': outstanding_id.id,
                'move_line_id': outstanding_id.move_line_id.id,
                'date': outstanding_id.payment_date,
                'amount_residual': outstanding_id.amount_residual,
                'allocation': amount_residual,
                'is_outstanding_line': True,
                'select': is_payment_line,
                'is_payment_line': is_payment_line,
            }

            common_id = self.env['common.allocation'].create(common_vals)
            common_ids += common_id
            outstanding_id.common_allocation_id = common_id.id

        for common_id in common_ids:
            if common_id.reference in invoice_data or common_id.move_id.ref in invoice_data:
                common_id.write({'select': True,'allocation':common_id.amount_residual})
        payment._compute_writeoff_amount()
        payment.with_context(from_payment_import= 1).action_process_payment_allocation()
        payment.message_post(body=_("Payment Import From File."))
        # DISPLAY ERRORS
        # if any(error_line_vals) and (context.get('validate') or context.get('importpayment')):
        #     self.env.cr.execute('''delete from importpayment_errorlines where importpayment_id=%s ''', (self.id,))
        #     self.exception = True
        #     _logger.info("Errors encountered.Payment cannot be initiated")
        #     self.errorline_ids = error_line_vals
        #     self.payment_file, self.payment_filename, self.state = '', '', 'exception'
        #     self.noexception = False

        # if self.noexception:
        #     master_payment_reg_list = dict()
        #     if payment_list:
        #         for each_payment in payment_list:
        #             if not master_payment_reg_list.has_key(each_payment['payment_method_id']):
        #                 ###append the master dict with key of payment id and call the function,
        #                 ###for the further filter based on check number
        #                 master_payment_reg_list[each_payment['payment_method_id']] = \
        #                     [self._group_for_check_and_manual
        #                      (filter(lambda r: r['payment_method_id'] == each_payment['payment_method_id'],
        #                              payment_list))]

        # if self.noexception:
        #     master_payment_reg_list = []
        #     check_lst = []
        #     can_edit_wizard = True
        #     for each_payment in payment_list:
        #         cur_vals_partner = each_payment.get('partner_id')
        #         cur_vals_pay_method = each_payment.get('payment_method_line_id')
        #         cur_vals_check = each_payment.get('communication', 0)
        #         flag = True
        #         index = 0
        #         is_append_dict = False
        #         new_dict = {}
        #         for master_data in master_payment_reg_list:
        #             data_partner = master_data.get('partner_id')
        #             data_pay_method = master_data.get('payment_method_line_id')
        #             data_check = master_data.get('communication', 0)
        #             data_discount = master_data.get('payment_term_discount', 0.0)
        #             data_amount = master_data.get('amount', 0.0)
        #             deduction_ids = master_data.get('deduction_ids',[])
        #             data_moves = master_data.get('line_ids', [])
        #             if cur_vals_partner == data_partner and cur_vals_pay_method == data_pay_method:
        #                 flag = False
        #                 if not cur_vals_check and not data_check:
        #                     master_payment_reg_list[index].update({
        #                         'amount': data_amount + each_payment.get('amount', 0.0),
        #                         'line_ids': list(set(data_moves + each_payment.get('line_ids', []))),
        #                         'deduction_ids': deduction_ids
        #                     })
        #                     i = 0
        #                     not_same_account = True
        #                     for deduction_id in master_payment_reg_list[index]['deduction_ids']:
        #                         for each_discount in each_payment.get('deduction_ids', []):
        #                             if 'deduction_ids' in master_payment_reg_list[index]:
        #                                 if deduction_id[2]['name'] == each_discount[2]['name'] and deduction_id[2]['account_id'] == each_discount[2]['account_id']:
        #                                     master_payment_reg_list[index]['deduction_ids'][i][2]['amount_currency'] += float(round(each_discount[2]['amount_currency'],2))
        #                                     master_payment_reg_list[index]['deduction_ids'][i][2]['amount_currency'] = round(master_payment_reg_list[index]['deduction_ids'][i][2]['amount_currency'],2)
        #                                     master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #                                     not_same_account = False
        #                             else:
        #                                 master_payment_reg_list[index]['deduction_ids'] = each_payment.get( 'deduction_ids', [])
        #                                 master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #                         i += 1
        #
        #                     if not_same_account:
        #                         if each_payment.get('deduction_ids', []):
        #                             master_payment_reg_list[index]['deduction_ids'].append(each_payment.get('deduction_ids', [])[0])
        #                             master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #
        #                     if 'deduction_ids' not in master_payment_reg_list[index] or not master_payment_reg_list[index]['deduction_ids']:
        #                         master_payment_reg_list[index]['deduction_ids'] = each_payment.get('deduction_ids', [])
        #                         master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #                 elif cur_vals_check:
        #                     if cur_vals_check == data_check:
        #                         if each_payment.get('deduction_ids',[]):
        #                             i = 0
        #                             not_same_account = True
        #                             for deduction_id in master_payment_reg_list[index]['deduction_ids']:
        #                                 for each_discount in each_payment.get('deduction_ids',[]):
        #                                     if 'deduction_ids' in master_payment_reg_list[index]:
        #                                         if deduction_id[2]['name'] == each_discount[2]['name'] and deduction_id[2]['account_id'] == each_discount[2]['account_id']:
        #                                             master_payment_reg_list[index]['deduction_ids'][i][2]['amount_currency'] += float(round(each_discount[2]['amount_currency'],2))
        #                                             master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #
        #                                             not_same_account = False
        #                                     else:
        #                                         master_payment_reg_list[index]['deduction_ids'] = each_payment.get('deduction_ids',[])
        #                                         master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #                                 i += 1
        #                             if not_same_account:
        #                                 if each_payment.get('deduction_ids', []):
        #                                     master_payment_reg_list[index]['deduction_ids'].append(each_payment.get('deduction_ids', [])[0])
        #                                     master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #                         master_payment_reg_list[index].update({
        #                             'amount': data_amount + each_payment.get('amount', 0.0),
        #                             'line_ids': list(set(data_moves + each_payment.get('line_ids', [])))
        #                         })
        #                         if 'deduction_ids' not in master_payment_reg_list[index] or not master_payment_reg_list[index]['deduction_ids']:
        #                             master_payment_reg_list[index]['deduction_ids'] = each_payment.get('deduction_ids',[])
        #                             master_payment_reg_list[index]['payment_difference_handling'] = each_payment.get('payment_difference_handling', 'reconcile_multi_deduct')
        #                     elif cur_vals_check not in check_lst:
        #                         is_append_dict = True
        #                         new_dict = each_payment
        #                         break
        #             index += 1
        #         if is_append_dict and new_dict:
        #             master_payment_reg_list.append(new_dict)
        #             is_append_dict = False
        #             new_dict = {}
        #             if each_payment.get('communication'):
        #                 check_lst.append(each_payment.get('communication'))
        #         if flag:
        #             can_edit_wizard = False
        #             master_payment_reg_list.append(each_payment)
        #             if each_payment.get('communication'):
        #                 check_lst.append(each_payment.get('communication'))
        #
        #     if master_payment_reg_list:
        #         # used_partner_moves = {}
        #         for every_item in master_payment_reg_list:
        #             final_every_item = self.get_refine_item(every_item)
        #             register_payment_obj = register_payment_obj.with_context( \
        #                 uid=self.env.uid, active_model='account.move.line', \
        #                 can_edit_wizard=can_edit_wizard,all_invoice_run=True,
        #                 search_disable_custom_filters=True, active_ids=final_every_item.get('line_ids'), \
        #                 active_id=final_every_item['line_ids'] if 'line_ids' in final_every_item else False)
        #             try:
        #                 # final_every_item['line_ids'] = self.env['account.move.line'].sudo().browse(final_every_item['line_ids'])
        #                 final_every_item['group_payment'] = True
        #                 payment = register_payment_obj.create(final_every_item)
        #                 # if not final_every_item['is_journal_entry']:
        #                 #     invoices_ids.append(final_every_item['invoice'].id)
        #                 # else:
        #                 #     journal_entry_ids.append(final_every_item['invoice'])
        #                 payment._create_payments()
        #
        #                 _logger.info("Invoice paid successfully")
        #             except Exception as E:
        #                 try:
        #                     error_msg = str(E)
        #                 except Exception as E:
        #                     error_msg = str(E)
        #                 raise exceptions.ValidationError(
        #                     _('%s\nAffected invoice number: %s') % (error_msg, values['Invoice Number']))

        # if context.get('account.payment.import'):
        #     # SHOW AFFECTED INVOICES LIST
        #     action = self.env.ref('account.action_account_payments') if pay_type == 'inbound' else self.env.ref('account.action_account_payments_payable')
        #     result = action.read()[0]
        #     action_journal_entry = self.env.ref('account.view_move_tree')
        #     result_journal_entry = action_journal_entry.read()[0]
        #     # if used_discount_move_lst:
        #     #     self.env.cr.execute('''UPDATE account_move_line
        #     #                                     SET is_used_discount = False WHERE id in (%s)''' % (
        #     #         ','.join(map(str, used_discount_move_lst))))
        #     if any(invoices_ids):
        #         result['domain'] = "[('id','in',[" + ','.join(map(str, invoices_ids)) + "])]"
        #     if any(journal_entry_ids):
        #         result_journal_entry['domain'] = "[('id','in',[" + ','.join(map(str, journal_entry_ids)) + "])]"
        #     return result if result else result_journal_entry
        # account_payment_view_tree = self.env.ref('account.view_account_payment_tree').id or False
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Payments',
        #     'res_model': 'account.payment',
        #     'views': [(account_payment_view_tree, 'tree')],
        #     'target': 'main',
        # }
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_payments')
        # action['domain'] = [('id', 'in', payment.ids)]
        return action
    
    def get_refine_item(self, every_item):
        final_dict = dict()
        total_residual = 0.00
        if not isinstance(every_item, dict):
            return final_dict
        final_dict = every_item.copy()
        if 'line_ids' in every_item:
            account_move_line = self.env['account.move.line'].browse(every_item['line_ids'])
            ##iterate through line and check amount residual
            moves_res = []
            for each in account_move_line:
                total_residual += each.amount_residual
                if not each.reconciled:
                    moves_res.append(each.id)
            if moves_res:
                final_dict.update({'line_ids': moves_res})

            # For Positive and negative payments reconcile.
            payment_type_res = final_dict.get('payment_type')
            partner_type_res = final_dict.get('partner_type')
            actual_payment_type_res = payment_type_res
            if partner_type_res == 'customer':
                actual_payment_type_res = 'outbound'
                if final_dict.get('amount') >= 0:
                    actual_payment_type_res = 'inbound'
            else:
                actual_payment_type_res = 'inbound'
                if final_dict.get('amount') > 0:
                    actual_payment_type_res = 'outbound'
            final_dict.update({'payment_type': actual_payment_type_res, 'amount': abs(every_item.get('amount'))})

            ##check condition for the total residual
            # if total_residual > 0:
            #     final_dict.update({'payment_type': 'inbound', 'amount': abs(every_item['amount'])})
            # else:
            #     final_dict.update({'payment_type': 'outbound', 'amount': abs(every_item['amount'])})
        return final_dict

    def parse_date(self, date_string):
        if date_string is None:
            return None
        if isinstance(date_string, float):
            date_string = self.excel_date_to_string(date_string)
        date_formats = ['%Y-%m-%d', '%m-%d-%Y', '%m-%d-%y', '%Y/%m/%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y']
        for date_format in date_formats:
            try:
                date = datetime.strptime(date_string, date_format)
                return date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None


    def excel_date_to_string(self, date_string):
        if isinstance(date_string, float):
            # Excel date starts from January 0, 1900
            base_date = datetime(1899, 12, 30)
            delta_days = timedelta(days=int(date_string))
            result_date = base_date + delta_days
            return result_date.strftime('%Y-%m-%d')

        return None



class Irattachment(models.Model):
    _inherit = 'ir.attachment'


    # @api.model
    # def check(self, mode, values=None):
    #     print("context??????",values)
    #     fsdfsdfd