from odoo import models, api,fields,_
from odoo.exceptions import UserError
from odoo.tools import format_amount, format_date, formatLang, groupby
from odoo.tools.float_utils import float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'



    def button_validate(self):
        """
        it is used to create invoice and payment for inter company purchase order.
        """
        res = super(StockPicking,self).button_validate()
        account_payment_register_obj = self.env['account.payment.register'].sudo()
        company_id = self.env['res.company'].search([('is_inter_company','=',True)])
        if company_id and self.picking_type_id.code == 'incoming':
            if self.company_id == company_id.secound_company_id and self.purchase_id.parent_company_id:
                self.purchase_id.action_create_invoice()
            if self.company_id == company_id.first_company_id and self.purchase_id.parent_company_id:
                self.purchase_id.action_create_invoice()
            if (self.company_id == company_id and self.purchase_id and
                    self.purchase_id.partner_id == company_id.first_company_id.partner_id):
                self.purchase_id.action_create_invoice()
            journal_id = self.env['account.journal'].search([('is_vendor_journal', '=', True)], limit=1).id
            for draft_invoice in self.purchase_id.invoice_ids.filtered(lambda inv: inv.state == 'draft'):
                draft_invoice.invoice_date = fields.Date.today()
                draft_invoice.action_post()
                payment_wizard = account_payment_register_obj.with_context(
                    active_ids = draft_invoice.line_ids.ids,
                    internal_order_ref=draft_invoice.internal_order_ref,
                    active_model = 'account.move.line',default_journal_id = journal_id).create({})
                payment_wizard.action_create_payments()
            # create customer invoice
            if company_id != self.company_id and self.purchase_id.parent_company_id:
                self.create_customer_invoice(self.purchase_id,company_id)
            # self._generate_invoice(self.purchase_id)

        return res

    def create_customer_invoice(self,purchase_id,parent_company_id):
        """
        it is used to create customer invoice.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        account_payment_register_obj = self.env['account.payment.register'].sudo()
        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        sequence = 10
        # self = purchase_id
        for order in purchase_id:
            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_customer_invoice(parent_company_id)
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                line_vals = line._prepare_account_move_line()
                line_vals.update({'quantity':line.product_qty,'purchase_line_id': False,'tax_ids': [(6, 0, line.product_id.taxes_id.ids)]})
                line_vals.update({'sequence': sequence})
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
        x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='out_invoice')
        journal_id = self.env['account.journal'].search([('is_customer_journal', '=', True)], limit=1).id
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)
            moves.action_post()
            payment_wizard = account_payment_register_obj.with_context(
                active_ids=moves.line_ids.ids,
                internal_order_ref=moves.internal_order_ref,
                active_model='account.move.line',default_journal_id = journal_id).create({})
            payment_wizard.action_create_payments()

