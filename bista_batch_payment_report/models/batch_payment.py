from fileinput import filename
from odoo import models, fields, api, _
import io
import base64
from datetime import datetime
from odoo.tools.misc import xlsxwriter
import re
from odoo.tools import float_round
from odoo.exceptions import ValidationError, UserError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"


    def print_batch_payment_excel_report(self):
        # Generate and download the Excel report.
        # Prepare header data
        header_data = {
            "company_name": self.journal_id.company_id.name,
            "journal_name": self.journal_id.name,
            "Batch/Out Number": self.name,
            "Date": self.date.strftime("%Y-%m-%d"),
            "Issuing Bank Account": self.journal_id.bank_acc_number or "",
            "bsb": self.journal_id.aba_bsb or "",
        }

        # Prepare transaction data
        transactions_data = []
        for payment in self.payment_ids:
            transactions_data.append({
                "Customer": payment.partner_id.name or "",
                "Date": payment.date.strftime("%d/%m/%Y"),
                "Memo": payment.ref or "",
                "Recipient Bank Account": payment.partner_bank_id.acc_number or "",
                "BSB": payment.partner_bank_id.aba_bsb or "",
                "Amount": payment.amount_signed,
            })

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Batch Payment")

        # Define date format
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'left'})
        large_font_format = workbook.add_format({"font_size": 13, "bold": True})

        # Write header
        worksheet.write(0, 0, header_data["company_name"],large_font_format)
        worksheet.write(0, 2, header_data["journal_name"], large_font_format)
        worksheet.write(1, 2, header_data["Batch/Out Number"], large_font_format)
        worksheet.write(2, 0, header_data["Date"])
        worksheet.write(4, 0, "Issuing Bank Account " + header_data["Issuing Bank Account"])
        worksheet.write(4, 2, "BSB " + header_data["bsb"])
        # worksheet.write(2, 0, "Issuing Bank Account")
        # worksheet.write(2, 1, header_data["Issuing Bank Account"])

        # Write table headers
        header_format = workbook.add_format({"bottom": 1})
        headers = ["Customer", "Date", "Memo", "Recipient Bank Account","BSB", "Amount"]
        for col, header in enumerate(headers):
            worksheet.write(6, col, header, header_format)

        # Track column widths
        column_widths = [len(header) for header in headers]

        # Write transaction data
        for row, transaction in enumerate(transactions_data, start=7):
            worksheet.write(row, 0, transaction["Customer"])
            worksheet.write_datetime(row, 1, datetime.strptime(transaction["Date"], "%d/%m/%Y"), date_format)
            worksheet.write(row, 2, transaction["Memo"])
            worksheet.write(row, 3, transaction["Recipient Bank Account"])
            worksheet.write(row, 4, transaction["BSB"])
            worksheet.write(row, 5, transaction["Amount"])

        # Update column widths
            column_widths[1] = max(column_widths[1], len(self.name))
            # column_widths[2] = max(column_widths[2], len(transaction["Memo"]))
            column_widths[3] = max(column_widths[3], len(transaction["Recipient Bank Account"]))
            column_widths[4] = max(column_widths[4], len(transaction["Memo"]))

        column_widths[0] = max(column_widths[0], len(header_data["company_name"]))
        # column_widths[4] = max(column_widths[4], len(header_data["Amount"]))
        column_widths[2] = max(column_widths[2], len(header_data["Batch/Out Number"])+4)

        # Write total
        total = sum(t["Amount"] for t in transactions_data)
        worksheet.write(len(transactions_data) + row, 4, "TOTAL")
        worksheet.write(len(transactions_data) + row, 5, total)

        # Adjust column widths based on content
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width + 2)  # Add padding for better readability

        # Finalize and encode file
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        filename = f"{self.name}.xlsx"
        output.close()

        self.message_post(
            attachments=[
                (filename, base64.decodebytes(file_data)),
            ]
        )

        # Create an attachment
        # self.env['ir.attachment'].create({
        #     'name': filename,
        #     'type': 'binary',
        #     'datas': file_data,
        #     'res_model': self._name,
        #     'res_id': self.id,
        # })

        # Return the report as a downloadable file
        # return {
        #     'type': 'ir.actions.act_url',
        #     'url': f'/web/content?model=ir.attachment&id={self.env["ir.attachment"].search([("res_model", "=", self._name), ("res_id", "=", self.id)], limit=1).id}&download=true',
        #     'target': 'new',
        # }

    """
    def print_batch_payment_excel_report(self):
        # data = self._generate_nacha_file()
        if self.payment_method_code == "nacha":
            header,entries = self._excel_generate_nacha_file()
            self._generate_excel_file(header,entries)
        else:
            self._excel_generate_export_file()
        return

    def _generate_excel_file(self,header,entries, footer_record = None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Batch Payment")

        # for col, header in enumerate(header):
        worksheet.set_column(0, 0, 110)
        worksheet.write(0, 0, header)
        for row, transaction in enumerate(entries, start=1):
            worksheet.write(row, 0, transaction.strip())

        if footer_record:
            worksheet.write(row+1, 0, footer_record.strip())

            # Finalize and encode file
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        filename = f"{self.name}.xlsx"
        output.close()

        self.message_post(
            attachments=[
                (filename, base64.decodebytes(file_data)),
            ]
        )

    def _excel_generate_nacha_file(self):
        journal = self.journal_id
        header = self._generate_nacha_header()
        entries = []
        batch_nr = 0

        offset_payments = self.env["account.payment"]
        for date, payments in sorted(self.payment_ids.grouped("date").items()):
            entries.append(self._generate_nacha_batch_header_record(date, batch_nr))

            for payment_nr, payment in enumerate(payments):
                self._validate_bank_for_nacha(payment)
                entries.append(self._generate_nacha_entry_detail(payment_nr, payment, is_offset=False))

            offset_payment = self.env["account.payment"]
            if journal.nacha_is_balanced:
                if not journal.bank_account_id:
                    raise ValidationError(_("Please set a bank account on the %s journal.", journal.display_name))

                offset_payment = self.env["account.payment"].new({
                    "partner_id": journal.company_id.partner_id.id,
                    "partner_bank_id": journal.bank_account_id.id,
                    "amount": sum(payment.amount for payment in payments),
                    "ref": "OFFSET",
                })
                self._validate_bank_for_nacha(offset_payment)
                offset_payments |= offset_payment
                entries.append(self._generate_nacha_entry_detail(len(payments), offset_payment, is_offset=True))

            entries.append(self._generate_nacha_batch_control_record(payments, offset_payment, batch_nr))
            batch_nr += 1

        entries.append(self._generate_nacha_file_control_record(batch_nr, self.payment_ids, offset_payments))
        entries.extend(self._generate_padding(batch_nr, len(self.payment_ids | offset_payments)))
        return header,entries

    def _excel_generate_export_file(self):
        self.ensure_one()
        if self.payment_method_code == 'aba_ct':
            bank_account = self.journal_id.bank_account_id
            if bank_account.acc_type != 'aba' or not bank_account.aba_bsb:
                raise UserError(_("The account %s, of journal '%s', is not valid for ABA.\nEither its account number is incorrect or it has no BSB set.", bank_account.acc_number, self.journal_id.name))

            if not self.journal_id.aba_fic or not self.journal_id.aba_user_spec or not self.journal_id.aba_user_number:
                raise UserError(_("The account %s, of journal '%s', is not set up for ABA payments.\nPlease fill in its ABA fields.", bank_account.acc_number, self.journal_id.name))

            for payment in self.payment_ids:
                if payment.partner_bank_id.acc_type != 'aba' or not payment.partner_bank_id.aba_bsb:
                    raise UserError(_("Bank account for payment '%s' has an invalid BSB or account number.", payment.name))
            header_record ,detail_summary, footer_record = self._excel_create_aba_document()
            self._generate_excel_file(header_record,detail_summary,footer_record)


    def _excel_create_aba_document(self):
        def _normalise_bsb(bsb):
            if not bsb:
                return ""
            test_bsb = re.sub('( |-)','',bsb)
            return '%s-%s' % (test_bsb[0:3],test_bsb[3:6])

        def to_fixed_width(string, length, fill=' ', right=False):
            return right and string[0:length].rjust(length, fill) or string[0:length].ljust(length, fill)

        def append_detail(detail_summary, detail_record, credit, debit):
            detail_summary['detail_records'].append(detail_record)
            if len(detail_summary['detail_records']) > 999997:
                raise UserError(_('Too many transactions for one ABA file - Please split in to multiple transfers'))
            detail_summary['credit_total'] += credit
            detail_summary['debit_total'] += debit
            if detail_summary['credit_total'] > 99999999.99 or detail_summary['debit_total'] > 99999999.99:
                raise UserError(_('The value of transactions is too high for one ABA file - Please split in to multiple transfers'))

        aba_date = max(fields.Date.context_today(self), self.date)
        header_record = '0' + (' ' * 17) + '01' \
                + to_fixed_width(self.journal_id.aba_fic, 3) \
                + (' ' * 7) \
                + to_fixed_width(self.journal_id.aba_user_spec, 26) \
                + to_fixed_width(self.journal_id.aba_user_number, 6, fill='0', right=True) \
                + to_fixed_width('PAYMENTS',12) \
                + aba_date.strftime('%d%m%y') \
                + (' ' * 40)

        detail_summary = {
            'detail_records': [],
            'credit_total': 0,
            'debit_total': 0,
            }

        aud_currency = self.env["res.currency"].search([('name', '=', 'AUD')], limit=1)
        bank_account = self.journal_id.bank_account_id
        for payment in self.payment_ids:
            credit = float_round(payment.amount, 2)
            debit = 0
            if credit > 99999999.99 or debit > 99999999.99:
                raise UserError(_('Individual amount of payment %s is too high for ABA file - Please adjust', payment.name))
            detail_record = '1' \
                    + _normalise_bsb(payment.partner_bank_id.aba_bsb) \
                    + to_fixed_width(payment.partner_bank_id.acc_number, 9, right=True) \
                    + ' ' + '50' \
                    + to_fixed_width(str(round(aud_currency.round(credit) * 100)), 10, '0', right=True) \
                    + to_fixed_width(payment.partner_bank_id.acc_holder_name or payment.partner_id.name, 32) \
                    + to_fixed_width(payment.ref or 'Payment', 18) \
                    + _normalise_bsb(bank_account.aba_bsb) \
                    + to_fixed_width(bank_account.acc_number, 9, right=True) \
                    + to_fixed_width(bank_account.acc_holder_name or self.journal_id.company_id.name, 16) \
                    + ('0' * 8)
            append_detail(detail_summary, detail_record, credit, debit)

        if self.journal_id.aba_self_balancing:
            # self balancing line use payment bank on both sides.
            credit = 0
            debit = detail_summary['credit_total']
            aba_date = max(fields.Date.context_today(self), self.date)
            detail_record = '1' \
                    + _normalise_bsb(bank_account.aba_bsb) \
                    + to_fixed_width(bank_account.acc_number, 9, right=True) \
                    + ' ' + '13' \
                    + to_fixed_width(str(round(aud_currency.round(debit) * 100)), 10, fill='0', right=True) \
                    + to_fixed_width(bank_account.acc_holder_name or self.journal_id.company_id.name, 32) \
                    + to_fixed_width('PAYMENTS %s' % aba_date.strftime('%d%m%y'), 18) \
                    + _normalise_bsb(bank_account.aba_bsb) \
                    + to_fixed_width(bank_account.acc_number, 9, right=True) \
                    + to_fixed_width(bank_account.acc_holder_name or self.journal_id.company_id.name, 16) \
                    + ('0' * 8)
            append_detail(detail_summary, detail_record, credit, debit)

        footer_record = '7' + '999-999' + (' ' * 12) \
                + to_fixed_width(str(round(aud_currency.round(abs(detail_summary['credit_total'] - detail_summary['debit_total'])) * 100)), 10, fill='0', right=True) \
                + to_fixed_width(str(round(aud_currency.round(detail_summary['credit_total']) * 100)), 10, fill='0', right=True) \
                + to_fixed_width(str(round(aud_currency.round(detail_summary['debit_total']) * 100)), 10, fill='0', right=True) \
                + (' ' * 24) \
                + to_fixed_width(str(len(detail_summary['detail_records'])), 6, fill='0', right=True) \
                + (' ' * 40)

        return header_record ,detail_summary['detail_records'], footer_record
        """

        
class AccountMoveInherit(models.Model):
    _inherit = "account.move"



    def _get_mail_template(self):
        """
        :return: the correct mail template based on the current move type
        """
        return (
            'bista_batch_payment_report.email_template_edi_credit_note'
            if all(move.move_type == 'out_refund' for move in self)
            else 'bista_batch_payment_report.email_template_edi_invoice'
        )