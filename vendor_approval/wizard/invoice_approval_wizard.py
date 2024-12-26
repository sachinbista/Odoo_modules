
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class account_send_approval_invoices(models.TransientModel):
    _name = "account.send.approval.invoices"
    
    invoice_ids = fields.Many2many('account.move', string='Invoices', copy=False)
    
    @api.model
    def default_get(self, fields):
        
        rec = super(account_send_approval_invoices, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        invoices = self.env['account.move'].browse(active_ids)
        
        # Check all invoices are Approved to Pay
        if len(invoices) == 1:
            for invoice in invoices:
                # for customer Invoices
                if invoice.move_type in ('out_invoice', 'out_refund', 'out_receipt','in_refund'):
                    raise UserError(_("You can not Send for Approval for posted customer invoices or vendor refunds"))
                # for Vendor Bills
                if invoice.move_type in ('in_invoice', 'in_receipt') and (invoice.state != 'posted' or invoice.payment_state != 'not_paid' or invoice.approval_status in ('send_approval','payment_to_pay')):
                    if invoice.approval_status in ('send_approval','payment_to_pay'):
                        raise UserError(_("%s Bill(s) is already sent for approval or approved to pay!!") % invoice.name)
                    raise UserError(_("You can only Send for Approval for posted and not paid bills, check bill: %s") % invoice.name)

        filtered_invoice_ids = [
            invoice.id for invoice in invoices
            if (
                    invoice.move_type in ('in_invoice', 'in_receipt') and
                    invoice.state == 'posted' and
                    invoice.payment_state == 'not_paid' and
                    invoice.approval_status not in ('send_approval', 'payment_to_pay')
            )
        ]
        rec.update({'invoice_ids': [(6, 0, filtered_invoice_ids)]})
        return rec
    
    # use this method to make invoices are send for approval
    def send_for_approval(self):
        for i in self.invoice_ids:
            i.write({'approval_status': 'send_approval'})
            
            
class account_approved_to_pay_invoices(models.TransientModel):
    _name = "account.approved.pay.invoices"
    
    invoice_ids = fields.Many2many('account.move', string='Bills', copy=False)
    
    @api.model
    def default_get(self, fields):
        
        rec = super(account_approved_to_pay_invoices, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        invoices = self.env['account.move'].browse(active_ids)
        
        # Check all invoices are Approved to Pay
        if any(invoice.approval_status != 'send_approval' for invoice in invoices):
            raise UserError(_("You can only Approved to Pay for Send for Approval bills"))
        
        rec.update({
                    'invoice_ids': [(6, 0, invoices.ids)],
                    })
        return rec

    # use this method to make invoices are Approved to Pay
    def approved_to_pay(self):
        if not self.user_has_groups('vendor_approval.group_approved_to_pay'):
            raise UserError(_("You do not have enough rights to perform this operation!!"))
        for i in self.invoice_ids:
            i.write({'approval_status': 'payment_to_pay'})


class cancel_approved_to_pay_invoices(models.TransientModel):
    _name = "cancel.approved.pay.invoices"

    @api.model
    def default_get(self, fields):
        
        rec = super(cancel_approved_to_pay_invoices, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        invoices = self.env['account.move'].browse(active_ids)

        for invoice in invoices:
            if invoice.move_type in ('out_invoice', 'out_refund', 'out_receipt','in_refund'):
                raise UserError(_("You can cancel vendor bills only!!"))

        return rec

    # use this method to move back to Send For Approval from Approve To Pay
    def cancel_approved_to_pay(self):
        if not self.user_has_groups('vendor_approval.group_approved_to_pay'):
            raise UserError(_("You do not have enough rights to perform this operation!"))
        active_ids = self._context.get('active_ids',False)
        invoice_recs = self.env['account.move'].browse(active_ids)

        for invoice in invoice_recs:
            if invoice.move_type in ('out_invoice', 'out_refund', 'out_receipt','in_refund'):
                raise UserError(_("You can cancel vendor bills only!!"))

            if invoice.move_type in ('in_invoice', 'in_receipt') and (invoice.approval_status != 'payment_to_pay' or invoice.payment_state != 'not_paid'):
                raise UserError(_("You can only Cancel Bills having state Approved to Pay!!"))
        invoice_recs.write({'approval_status': 'cancel_approval_to_pay'})
