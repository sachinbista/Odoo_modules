from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    batch_type = fields.Selection(
        selection=[('inbound', 'Inbound'), ('outbound', 'Outbound'),
                   ('inbound_outbound', 'Inbound/Outbound')],
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default='inbound', tracking=True)

    @api.onchange('batch_type', 'payment_method_id', 'journal_id')
    def onchange_inbound_outbound_domain(self):
        if self.batch_type == 'inbound_outbound':
            return {"domain": {
                "payment_ids": [('payment_type', 'in', ['inbound',
                                                        'outbound']),
                                ('batch_payment_id', '=', False),
                                ('state', '=', 'posted'),
                                ('is_move_sent', '=', False),
                                ('amount', '!=', 0),
                                ('journal_id', '=', self.journal_id.id)]}}
        elif self.batch_type in ['inbound', 'outbound']:
            return {"domain": {
                "payment_ids": [('payment_type', '=', self.batch_type),
                                ('batch_payment_id', '=', False),
                                ('state', '=', 'posted'),
                                ('is_move_sent', '=', False),
                                ('amount', '!=', 0),
                                ('journal_id', '=', self.journal_id.id),
                                ('payment_method_id', '=',
                                 self.payment_method_id.id)]}}

    @api.constrains('batch_type', 'journal_id', 'payment_ids')
    def _check_payments_constrains(self):
        for record in self:
            all_companies = set(record.payment_ids.mapped('company_id'))
            if len(all_companies) > 1:
                raise ValidationError(
                    _("All payments in the batch must belong to the same "
                      "company."))
            all_journals = set(record.payment_ids.mapped('journal_id'))
            if len(all_journals) > 1 or (
                    record.payment_ids and record.payment_ids[
                                           :1].journal_id != record.journal_id):
                raise ValidationError(
                    _("The journal of the batch payment and of the payments it "
                      "contains must be the same."))
            all_types = set(record.payment_ids.mapped('payment_type'))
            if all_types and record.batch_type not in all_types:
                if record.batch_type != 'inbound_outbound':
                    raise ValidationError(
                        _("The batch must have the same type as the payments "
                          "it contains."))
            all_payment_methods = record.payment_ids.payment_method_id
            if len(all_payment_methods) > 1:
                if record.batch_type != 'inbound_outbound':
                    raise ValidationError(
                        _("All payments in the batch must share the same "
                          "payment method."))
            if (all_payment_methods and record.payment_method_id not in
                    all_payment_methods):
                raise ValidationError(
                    _("The batch must have the same payment method as the "
                      "payments it contains."))
            payment_null = record.payment_ids.filtered(lambda p: p.amount == 0)
            if payment_null:
                raise ValidationError(
                    _('You cannot add payments with zero amount in a Batch '
                      'Payment.'))
            non_posted = record.payment_ids.filtered(
                lambda p: p.state != 'posted')
            if non_posted:
                raise ValidationError(
                    _('You cannot add payments that are not posted.'))

    def _generate_nacha_file(self):
        if self.env.company.id == 1:
            header = self._generate_nacha_header()
            entries = []
            n = 0
            for batch_nr, payment in enumerate(self.payment_ids):
                self._validate_payment_for_nacha(payment)
                self._validate_bank_for_nacha(payment)
                if n == 0:
                    entries.append(self._generate_nacha_batch_header_record(payment, batch_nr))
                    n = n + 1
                entries.append(self._generate_nacha_entry_detail(payment,batch_nr))
            # entries.append(self._generate_nacha_batch_control_record(payment, batch_nr))

            entries.append(self._generate_nacha_file_control_record(self.payment_ids))
            entries.extend(self._generate_padding(self.payment_ids))
            return "\r\n".join([header] + entries)


        elif self.env.company.id in [2, 3]:
            header = self._generate_nacha_header()
            entries = []
            total_payments = len(self.payment_ids)
            n = 0
            for batch_nr, payment in enumerate(self.payment_ids):
                self._validate_payment_for_nacha(payment)
                self._validate_bank_for_nacha(payment)
                # print("batch_nrbatch_nr",batch_nr)
                if n == 0:
                    entries.append(self._generate_nacha_batch_header_record(payment, batch_nr))
                    n = n + 1
                entries.append(self._generate_nacha_entry_detail(payment, batch_nr))
                if batch_nr == (total_payments - 1):
                    entries.append(self._generate_nacha_batch_control_record(payment, batch_nr))

            entries.append(self._generate_nacha_file_control_record(self.payment_ids))
            entries.extend(self._generate_padding(self.payment_ids))
            return "\r\n".join([header] + entries)

        else:
            header = self._generate_nacha_header()
            entries = []
            for batch_nr, payment in enumerate(self.payment_ids):
                self._validate_payment_for_nacha(payment)
                self._validate_bank_for_nacha(payment)
                # print("batch_nrbatch_nr",batch_nr)
                entries.append(self._generate_nacha_batch_header_record(payment, batch_nr))
                entries.append(self._generate_nacha_entry_detail(payment,batch_nr))
                entries.append(self._generate_nacha_batch_control_record(payment, batch_nr))

            entries.append(self._generate_nacha_file_control_record(self.payment_ids))
            entries.extend(self._generate_padding(self.payment_ids))
            return "\r\n".join([header] + entries)

    def _generate_nacha_batch_header_record(self, payment, batch_nr):
        if self.env.company.id in [2, 3]:
            total_payments = len(self.payment_ids)
            # print("ddddddddddddddd",batch_nr,total_payments - 1)
            batch = []
            batch.append("5")  # Record Type Code
            batch.append("220")  # Service Class Code (credits only)
            batch.append("{:16.16}".format(self.journal_id.company_id.name))  # Company Name
            batch.append("{:20.20}".format(""))  # Company Discretionary Data (optional)
            batch.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
            batch.append("PPD")  # Standard Entry Class Code
            batch.append("{:10.10}".format(payment.ref))  # Company Entry Description
            batch.append("{:6.6}".format(payment.date.strftime("%y%m%d")))  # Company Descriptive Date
            batch.append("{:6.6}".format(payment.date.strftime("%y%m%d")))  # Effective Entry Date
            batch.append("{:3.3}".format(""))  # Settlement Date (Julian)
            batch.append("1")  # Originator Status Code
            batch.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
            batch.append("{:07d}".format(total_payments))  # Batch Number
            return "".join(batch)
        else:
            batch = []
            batch.append("5")  # Record Type Code
            batch.append("220")  # Service Class Code (credits only)
            batch.append("{:16.16}".format(self.journal_id.company_id.name))  # Company Name
            batch.append("{:20.20}".format(""))  # Company Discretionary Data (optional)
            batch.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
            batch.append("PPD")  # Standard Entry Class Code
            batch.append("{:10.10}".format(payment.ref))  # Company Entry Description
            batch.append("{:6.6}".format(payment.date.strftime("%y%m%d")))  # Company Descriptive Date
            batch.append("{:6.6}".format(payment.date.strftime("%y%m%d")))  # Effective Entry Date
            batch.append("{:3.3}".format(""))  # Settlement Date (Julian)
            batch.append("1")  # Originator Status Code
            batch.append(
                "{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
            batch.append("{:07d}".format(batch_nr))  # Batch Number

            return "".join(batch)

    def _generate_nacha_batch_control_record(self, payment, batch_nr):
        if self.env.company.id in [2, 3]:
            total_payments = len(self.payment_ids)
            total_amount = 0.0
            for payment in self.payment_ids:
                total_amount += payment.amount
            bank = payment.partner_bank_id
            control = []
            control.append("8")  # Record Type Code
            control.append("220")  # Service Class Code (credits only)
            control.append("{:06d}".format(1))  # Entry/Addenda Count
            control.append("{:010d}".format(self._calculate_aba_hash(bank.aba_routing)))  # Entry Hash
            control.append("{:012d}".format(0))  # Total Debit Entry Dollar Amount in Batch
            control.append("{:012d}".format(round(total_amount * 100)))  # Total Credit Entry Dollar Amount in Batch
            control.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
            control.append("{:19.19}".format(""))  # Message Authentication Code (leave blank)
            control.append("{:6.6}".format(""))  # Reserved (leave blank)
            control.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
            control.append("{:07d}".format(total_payments))  # Batch Number
            return "".join(control)
        else:
            bank = payment.partner_bank_id
            control = []
            control.append("8")  # Record Type Code
            control.append("220")  # Service Class Code (credits only)
            control.append("{:06d}".format(1))  # Entry/Addenda Count
            control.append("{:010d}".format(self._calculate_aba_hash(bank.aba_routing)))  # Entry Hash
            control.append("{:012d}".format(0))  # Total Debit Entry Dollar Amount in Batch
            control.append("{:012d}".format(round(payment.amount * 100)))  # Total Credit Entry Dollar Amount in Batch
            control.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
            control.append("{:19.19}".format(""))  # Message Authentication Code (leave blank)
            control.append("{:6.6}".format(""))  # Reserved (leave blank)
            control.append(
                "{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
            control.append("{:07d}".format(batch_nr))  # Batch Number
            return "".join(control)

    def _generate_nacha_entry_detail(self, payment,batch_nr):
        if self.env.company.id in [2, 3]:
            bank = payment.partner_bank_id
            entry = []
            entry.append("6")  # Record Type Code (PPD)
            entry.append("22")  # Transaction Code
            entry.append("{:8.8}".format(bank.aba_routing[:-1]))  # RDFI Routing Transit Number
            entry.append("{:1.1}".format(bank.aba_routing[-1]))  # Check Digit
            entry.append("{:17.17}".format(bank.acc_number))  # DFI Account Number
            entry.append("{:010d}".format(round(payment.amount * 100)))  # Amount
            entry.append("{:15.15}".format(payment.partner_id.vat or ""))  # Individual Identification Number (optional)
            entry.append("{:22.22}".format(payment.partner_id.name))  # Individual Name
            entry.append("  ")  # Discretionary Data Field
            entry.append("0")  # Addenda Record Indicator
            # trace number
            entry.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Trace Number (80-87)
            entry.append("{:07d}".format(batch_nr))  # Trace Number (88-94)
            return "".join(entry)
        else:
            bank = payment.partner_bank_id
            entry = []
            entry.append("6")  # Record Type Code (PPD)
            entry.append("22")  # Transaction Code
            entry.append("{:8.8}".format(bank.aba_routing[:-1]))  # RDFI Routing Transit Number
            entry.append("{:1.1}".format(bank.aba_routing[-1]))  # Check Digit
            entry.append("{:17.17}".format(bank.acc_number))  # DFI Account Number
            entry.append("{:010d}".format(round(payment.amount * 100)))  # Amount
            entry.append("{:15.15}".format(payment.partner_id.vat or ""))  # Individual Identification Number (optional)
            entry.append("{:22.22}".format(payment.partner_id.name))  # Individual Name
            entry.append("  ")  # Discretionary Data Field
            entry.append("0")  # Addenda Record Indicator
            # trace number
            entry.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Trace Number (80-87)
            entry.append("{:07d}".format(0))  # Trace Number (88-94)
            return "".join(entry)
