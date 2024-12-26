##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api


class ShopifyWorkflowProcess(models.Model):
    _name = "shopify.workflow.process"
    _description = "Shopify Auto Workflow Process"

    @api.model
    def _default_journal(self):
        """
            This method will return sales journal of currant company.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        account_journal_obj = self.env['account.journal']
        company_id = self._context.get('company_id', self.env.company.id)
        domain = [('type', '=', "sale"), ('company_id', '=', company_id)]
        return account_journal_obj.search(domain, limit=1)

    name = fields.Char(string='Name')
    confirm_order = fields.Boolean("Confirm Order", copy=False)
    create_invoice = fields.Boolean('Create Invoice', copy=False)
    validate_invoice = fields.Boolean('Validate Invoice', copy=False)
    register_payment = fields.Boolean("Register Payment", copy=False)
    company_id = fields.Many2one('res.company', string='Company', help='Company', default=lambda self: self.env.company)
    pay_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                     domain=[('type', 'in', ['cash', 'bank'])])
    sale_journal_id = fields.Many2one('account.journal', string='Sales Journal',
                                      default=_default_journal)
    credit_note_journal_id = fields.Many2one('account.journal', 'Credit Note Journal')
    shipping_policy = fields.Selection(
        [('direct', 'Deliver each product when available'),
         ('one', 'Deliver all products at once')], string='Shipping Policy',
        default="one")
    in_pay_method_id = fields.Many2one('account.payment.method',
                                       string="Payment Method",
                                       domain=[('payment_type', '=', 'inbound')])
    payment_method_line_id = fields.Many2one('account.payment.method.line',
                                             string='Payment Method',copy=False)

    @api.onchange('confirm_order')
    def onchange_confirm_order(self):
        for rec in self:
            if not rec.confirm_order:
                rec.create_invoice = False

    @api.onchange('create_invoice')
    def onchange_create_invoice(self):
        for rec in self:
            if not rec.create_invoice:
                rec.validate_invoice = False

    @api.onchange('validate_invoice')
    def onchange_validate_invoice(self):
        for rec in self:
            if not rec.validate_invoice:
                rec.register_payment = False

    @api.onchange('register_payment')
    def onchange_register_payment(self):
        for rec in self:
            if not rec.register_payment:
                rec.pay_journal_id = None
                rec.in_pay_method_id = None
