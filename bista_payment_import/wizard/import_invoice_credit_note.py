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


class importinvoice_errorlines(models.TransientModel):
    _name = 'importinvoice.errorlines'
    _description = 'Show error logs after import Invoice'

    importinvoice_id = fields.Many2one('account.invoice.import', 'Error Line')
    rowline = fields.Integer('Row number')
    comment = fields.Text('Exception')


class AccountInvoiceImport(models.TransientModel):
    _name = "account.invoice.import"
    _description = "Account Payment Import from CSV"

    csv_import = fields.Boolean(default=True, readonly=True)
    invoice_file = fields.Binary(
        string="Import XLSX File",
        required=True,
        help="Upload a Request for Payment. Supported "
        "formats: CSV.",
    )
    invoice_filename = fields.Char(string="Filename")
    is_new_invoice = fields.Boolean("Allow New Entry", default=True)
    is_vendor_bill = fields.Boolean("Is Vendor Bill",default=False)
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
    errorline_ids = fields.One2many('importinvoice.errorlines', 'importinvoice_id', string='Error lines')
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
                        discount_amount = abs(self.validate_amountvalue(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['discount_amount']))
                        net_amount = self.validate_amountvalue(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['net_amount'])
                        discount_percentage = 0
                        if discount_amount > 0:
                            # discount_percentage = round(((abs(discount_amount) * 100) / abs(gross_amount)), 2)
                            lines.append((0, 0, {
                                'name': 'Discount',
                                'quantity': 1,
                                'price_unit': -abs(discount_amount),
                                'account_id': int(invoice_vals[invoice_val]['discount_account']),
                                'tax_ids': [(6, 0, [])],
                                'analytic_distribution': invoice_vals[invoice_val]['invoice_lines'][invoice_line][
                                    'analytic_distribution'],

                            }))

                        lines.append((0, 0, {
                                'name': invoice_vals[invoice_val]['invoice_lines'][invoice_line]['description'],
                                'quantity': 1,
                                'price_unit': abs(gross_amount),
                                'account_id': int(invoice_vals[invoice_val]['invoice_lines'][invoice_line]['income_account_id']),
                                'tax_ids': [(6, 0, [])],
                                'analytic_distribution': invoice_vals[invoice_val]['invoice_lines'][invoice_line]['analytic_distribution'],
                                'discount': discount_percentage,

                            }))



                    invoice = self.env['account.move'].sudo().create({
                        'partner_id': partner.id,
                        'ref': invoice_val,
                        'po_reference': invoice_vals[invoice_val]['po_number'] if 'po_number' in invoice_vals[invoice_val] else invoice_val,
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
            self._cr.execute('''SELECT id FROM account_move WHERE name='%s' or ref='%s' or po_reference='%s' LIMIT 1''' % (invoice_number, invoice_number, invoice_number))
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
        file_name = self.invoice_filename.split('.')
        if file_name[-1] != 'csv':
            raise exceptions.ValidationError(_("Not a valid file!"))
        data = base64.b64decode(self.invoice_file)
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
            file_data = base64.b64decode(self.invoice_file)
            book = xlrd.open_workbook(file_contents=file_data)
        except FileNotFoundError:
            raise UserError('No such file or directory found. \n%s.' % self.invoice_filename)
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


    def action_invoice_validate_button(self):
        error_line_vals = self.action_import_invoice_credit_note(dryrun=True)
        context = self.env.context
        if any(error_line_vals) and (context.get('validate') or context.get('account.invoice.import')):
            self.env.cr.execute('''delete from importinvoice_errorlines where importinvoice_id=%s ''', (self.id,))
            self.exception = True
            _logger.info("Errors encountered.Payment cannot be initiated")
            self.errorline_ids = error_line_vals
            self.invoice_file, self.invoice_filename, self.state = '', '', 'exception'
            self.noexception = False
        else:
            self.env.cr.execute('''delete from importinvoice_errorlines where importinvoice_id=%s ''', (self.id,))
            self.noexception, self.exception, self.state = True, False, 'noexception'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice.import',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    # TODO: add tests
    def action_import_invoice_credit_note(self, dryrun=False):
        """ This function is use to import payment from CSV file."""
        self.ensure_one()

        context = self.env.context
        invoice_obj = self.env['account.move']
        account_obj = self.env['account.account']
        analytic_account_obj = self.env['account.analytic.account']
        user_obj = self.env['res.users']
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

        if not discount_account_id:
            error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                           'comment': 'Discount Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.' , \
                                           'rowline': ''}])

        if not writeoff_account_id:
            error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                           'comment': 'Write Off Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.' , \
                                           'rowline': ''}])

        if not self.invoice_file:
            raise exceptions.Warning(_("You need to select a file!"))
            # DECODE THE FILE DATA

        if self.import_option == 'csv':
            reader_info,keys = self.get_csv_file_data()
        else:
            reader_info,keys = self.get_excel_file_data()

            # file_name = self.invoice_filename.split('.')
            # if file_name[-1] != 'csv':
            #     raise exceptions.ValidationError(_("Not a valid file!"))
            # data = base64.b64decode(self.invoice_file)
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

        self._cr.execute('SAVEPOINT invoicecreditimport')
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
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, 'comment': 'There is some problem in this line %s' % (
                                                    values['Invoice Number']), 'rowline': rownumber}])
            # Check Analytic Account
            analytic_distribution = {}
            if 'Analytic Account' in values and values['Analytic Account'] != '':
                analytic_account_id = analytic_account_obj.with_company(company).search(['|',('name', '=', values['Analytic Account']),('code', '=', values['Analytic Account'])])
                if not analytic_account_id:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Analytic Account %s not found for invoice %s' % (
                                                   values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(analytic_account_id) > 1:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Duplicate Analytic Account %s found for invoice %s' % (
                                                       values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])
                if len(analytic_account_id) == 1:
                    analytic_distribution = {analytic_account_id.id: 100}

                if 'Analytic Distribution' in values and not values['Analytic Distribution']:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, 'comment': 'Analytic Distribution %s found for invoice %s' % (
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
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Income Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                               'rowline': ''}])

            if any(error_line_vals) and (context.get('validate') or context.get('account.payment.import')):
                self.env.cr.execute('''delete from importinvoice_errorlines where importinvoice_id=%s ''', (self.id,))
                self.exception = True
                _logger.info("Errors encountered.Payment cannot be initiated")
                self.errorline_ids = error_line_vals
                self.invoice_file, self.invoice_filename, self.state = '', '', 'exception'
                self.noexception = False
            else:
                self.env.cr.execute('''delete from importinvoice_errorlines where importinvoice_id=%s ''', (self.id,))
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

                        if 'Discount Account' in values and values['Discount Account'] != '':
                            discount_account = str(values['Discount Account'])
                            discount_account = discount_account.split('.')[0]
                            discount_account = discount_account.split(',')[0]
                            discount_account_id = account_obj.search([('code', '=', discount_account), ('deprecated', '=', False),('company_id', '=', company.id)])
                            if discount_account_id:
                                invoice_data[value_of_invoice_number.strip()]['discount_account'] = discount_account_id.id

                        invoice_data[value_of_invoice_number.strip()]['partner'] = values['Partner']
                        invoice_data[value_of_invoice_number.strip()]['po_number'] = values['P/O Number']
                        invoice_data[value_of_invoice_number.strip()]['invoice_date'] = self.parse_date(values['Invoice Date'])
                        invoice_data[value_of_invoice_number.strip()]['gross_amount'] = self.validate_amountvalue(values['Gross Amount'])
                        invoice_data[value_of_invoice_number.strip()]['net_amount'] = self.validate_amountvalue(values['Net Amount'])
                        invoice_data[value_of_invoice_number.strip()]['discount_amount'] = self.validate_amountvalue(values['Discount Amount'])
                        # invoice_data[value_of_invoice_number.strip()]['writeoff_amount'] = self.validate_amountvalue(values['WHT Amount'])
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'] = {}
                        invoice_data[value_of_invoice_number.strip()]['invoice_lines'][i] = {'ref': str(value_of_invoice_number), 'Partner': values['Partner'], 'invoice_date': self.parse_date(values['Invoice Date']), 'description': values['Invoice Description'], 'gross_amount': self.validate_amountvalue(values['Gross Amount']), 'income_account_id': income_account_id, 'analytic_distribution': analytic_distribution,'discount_amount':self.validate_amountvalue(values['Discount Amount']),'net_amount':self.validate_amountvalue(values['Net Amount'])}
                    else:
                        if 'Discount Account' in values and values['Discount Account'] != '':
                            discount_account = str(values['Discount Account'])
                            discount_account = discount_account.split('.')[0]
                            discount_account = discount_account.split(',')[0]
                            discount_account_id = account_obj.search([('code', '=', discount_account), ('deprecated', '=', False),('company_id', '=', company.id)])
                            if discount_account_id:
                                invoice_data[value_of_invoice_number.strip()]['discount_account'] = discount_account_id.id

                        invoice_data[value_of_invoice_number.strip()]['po_number'] = values['P/O Number']
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
                        error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                       'comment': 'Invoice number %s already paid' % (
                                                           values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    elif invoice.state != 'posted' and not dryrun:
                        error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
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
                            error_line_vals.append([0, 0, {'importinvoice_id': self.id,
                                                           'comment': 'Partner is missing in journal item for Invoice number %s.' \
                                                                      % (values['Invoice Number']),
                                                           'rowline': rownumber}])
                            continue
                        commercial_partner_id = sale_journal_entry and sale_journal_entry.partner_id and sale_journal_entry.partner_id.commercial_partner_id
                    if not sale_journal_entry:
                        error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                       'comment': 'Invoice Number %s not found' % (
                                                           values['Invoice Number']), \
                                                       'rowline': rownumber}])
                        continue
                    else:
                        is_journal_entry = True
                        commercial_partner_id = sale_journal_entry.partner_id

            else:
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Invoice number not found in csv sheet',
                                               'rowline': rownumber}])
                # continue

            if invoice and invoice.partner_id.name != values['Partner']:
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Partner name not matching with invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])

            # date = datetime.strptime(values['Invoice Date'], "%m-%d-%Y").date()
            date = self.parse_date(values['Invoice Date'])
            if invoice and str(invoice.invoice_date) != date:
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Invoice date not matching for invoice %s' % (
                                                   invoice.ref), \
                                               'rowline': rownumber}])

                # CHECK GROSS AMOUNT
            if not values['Gross Amount'] or values['Gross Amount'] == '0':
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Gross Amount not found in csv sheet for invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue
            gross_amount = self.validate_amountvalue(values['Gross Amount'])
            if not gross_amount:
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Invalid gross amount %s for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue

            if values['Gross Amount'] and float(self.validate_amountvalue(values['Gross Amount']))< 0 and float(self.validate_amountvalue(values['Net Amount'])) > 0:
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Invalid Net amount %s for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])

                # continue
            # CHECK NET AMOUNT
            if not values['Net Amount'] or values['Net Amount'] == '0':
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Net Amount not found in csv sheet for invoice %s' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue

            net_amount = self.validate_amountvalue(values['Net Amount'])
            if not net_amount:
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Invalid net amount %s found in csv sheet for invoice %s' % (
                                                   values['Net Amount'], values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue
            discount_amount = self.validate_amountvalue(values['Discount Amount'])
            if is_journal_entry and receivable_account_ids:
                # self.env.cr.execute('''select COALESCE(sum(debit-credit), 0.0) from account_move_line where ''' \
                #                     '''move_id=%s and account_id in %s''', \
                #                     (sale_journal_entry.id, receivable_account_ids))
                # amount_total_signed = map(lambda x: x[0], self.env.cr.fetchall())
                amount_total_signed = self.get_signed_amount(sale_journal_entry, receivable_account_ids)
                if round(gross_amount,1) != round(amount_total_signed[0],1):
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
                    #     error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                    #                                    'comment': 'Gross amount mismatch for invoice %s.\n' \
                    #                                               'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                    #                                               % (values['Invoice Number'], values['Gross Amount'],
                    #                                                  amount_total_signed), \
                    #                                    'rowline': rownumber}])
                    #     continue
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Gross amount mismatch for invoice %s.\n' \
                                                              'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                                                              % (values['Invoice Number'], values['Gross Amount'],
                                                                 amount_total_signed), \
                                                   'rowline': rownumber}])
                    # continue
            elif invoice and round(gross_amount,2) != round(invoice.amount_total_signed + discount_amount, 2):
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Gross amount mismatch for invoice %s.\n' \
                                                          'Gross amount in csv sheet: %s\nGross amount in Odoo: %s' \
                                                          % (values['Invoice Number'], values['Gross Amount'],
                                                             invoice.amount_total_signed), \
                                               'rowline': rownumber}])

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
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                               'comment': 'Vendor invoice %s cannot be imported from customer window' % (
                                                   values['Invoice Number']), \
                                               'rowline': rownumber}])
                # continue
            elif context.get('transaction_type') == 'outbound' and pay_type == 'inbound':
                error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
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
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Discount Account %s not found for invoice %s' % (discount_account, values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(discount_account_id) > 1:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Duplicate Discount Account %s found for invoice %s' % (discount_account,
                                                       values['Invoice Number']), \
                                                   'rowline': rownumber}])
            # Check Analytic Account
            if 'Analytic Account' in values and values['Analytic Account'] != '':
                analytic_account_id = analytic_account_obj.search(['|',('name', '=', values['Analytic Account']),('code', '=', values['Analytic Account']),('company_id', '=' , company.id)])
                if not analytic_account_id:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Analytic Account not found for invoice %s' % (values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(analytic_account_id) > 1:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Duplicate Analytic Account %s found' % (
                                                       values['Analytic Account']), \
                                                   'rowline': rownumber}])

                if 'Analytic Distribution' in values and not values['Analytic Distribution']:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Analytic Distribution %s found' % (
                                                       values['Analytic Distribution']), \
                                                   'rowline': rownumber}])

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


                    # continue
                # if payment_vals.get('communication') and commercial_partner_id:
                #     is_allow_check = self.allow_check_number(payment_vals.get('communication'), commercial_partner_id.id)
                #     if not is_allow_check:
                #         error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                #                                        'comment': 'You have already use same check number for another partner.\n' \
                #                                                   'Check number is %s.'
                #                                                   % (values['Check Number']),
                #                                        'rowline': rownumber}])
                        # continue

            # PAYMENT VIA DISCOUNT
            if values['Discount Amount'] and values['Discount Amount'] and not self.validate_amountvalue(values['Discount Amount']) == 0.0:
                if not self.validate_amountvalue(values['Discount Amount']):
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Invalid discount amount %s found for invoice %s.' \
                                                              % (values['Discount Amount'], values['Invoice Number']),
                                                   'rowline': rownumber}])

                if values['Gross Amount'] and float(self.validate_amountvalue(values['Gross Amount']))< 0:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
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
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Discount Account not found for invoice %s' % (
                                                   values['Invoice Number']), \
                                                   'rowline': rownumber}])


            # if values['Discount Amount'] and float(values['Discount Amount']) > 0 and values['WHT Amount'] and float(values['WHT Amount']) > 0:
            #     error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
            #                                    'comment': 'Discount amount and WHT amount both can not be used together for invoice %s.' \
            #                                               % (values['Invoice Number']),
            #                                    'rowline': rownumber}])


            # For (Gross Amount - Net Amount) is less than or equal to 0.01.
            gross_amt = float(self.validate_amountvalue(values['Gross Amount'])) if values['Gross Amount'] else 0.0
            disc_amt = float(self.validate_amountvalue(values['Discount Amount'])) if values['Discount Amount'] else 0.0
            net_amt = float(self.validate_amountvalue(values['Net Amount'])) if values['Net Amount'] else 0.0

            # if net_amt < 0:
            #     error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
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



        if dryrun:
            self._cr.execute('ROLLBACK TO SAVEPOINT invoicecreditimport')
            # cancel all changes done to the registry/ormcache
            self.pool.clear_caches()
            self.pool.reset_changes()
        else:
            self._cr.execute('RELEASE SAVEPOINT invoicecreditimport')

        return error_line_vals



    def action_make_invoice_button(self):
        self.action_import_invoice_credit_note(dryrun=False)
        inv_ids = self.action_make_invoice_credit_note()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('move_type', 'in', ('out_invoice', 'out_refund')),('id','in',inv_ids)]
        return action

    def action_make_invoice_credit_note(self):
        context = self.env.context
        invoice_obj = self.env['account.move']
        account_obj = self.env['account.account']
        analytic_account_obj = self.env['account.analytic.account']
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
        if not self.invoice_file:
            raise exceptions.ValidationError(_("You need to select a file!"))
        # DECODE THE FILE DATA
        if self.import_option == 'csv':
            reader_info,keys = self.get_csv_file_data()
        else:
            reader_info,keys = self.get_excel_file_data()
        # data = base64.b64decode(self.invoice_file)
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

        if not discount_account_id:
            error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                           'comment': 'Discount Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                           'rowline': ''}])

        if not writeoff_account_id:
            error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                           'comment': 'Write Off Account not set in the configuration. Please check in the Account -> Setting -> Configuration - The following default accounts are used with certain features.', \
                                           'rowline': ''}])

        if not income_account_id:
            error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
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
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Analytic Account %s not found for invoice %s' % (
                                                       values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])
                    # continue
                if len(analytic_account_id) > 1:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id, \
                                                   'comment': 'Duplicate Analytic Account %s found for invoice %s' % (
                                                       values['Analytic Account'], values['Invoice Number']), \
                                                   'rowline': rownumber}])

                if 'Analytic Distribution' in values and not values['Analytic Distribution']:
                    error_line_vals.append([0, 0, {'importinvoice_id': self.id,
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


        # action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        # action['domain'] = [('move_type', 'in', ('out_invoice', 'out_refund')),('id','in',inv_ids)]
        return inv_ids
    
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