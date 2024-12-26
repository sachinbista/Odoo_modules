# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class UpdateInvoiceAccountWiz(models.TransientModel):
    _name = 'update.invoice.account.wiz'
    _description = 'Update Invoice GL Account'

    @api.model
    def default_get(self, fields):
        defaults = super(UpdateInvoiceAccountWiz,  self).default_get(fields)
        account_move_id = self.env['account.move'].browse(self.env.context.get('active_id'))
        line_vals=[]
        if account_move_id:
            for aml_id in account_move_id.invoice_line_ids:
                line_vals.append((0, 0, {'aml_id': aml_id.id,
                                         'product_id': aml_id.product_id.id,
                                         'label': aml_id.name,
                                         'account_id': aml_id.account_id.id}))
                                            
        if self._context.get('active_model') == 'account.move' and account_move_id:
            defaults.update({'account_move_id': account_move_id.id,
                             'company_id': account_move_id.company_id.id,
                             'update_invoice_line': line_vals,
                             })
        return defaults

    account_move_id = fields.Many2one('account.move', string='Invoice')
    company_id = fields.Many2one('res.company', string='Company')
    update_invoice_line = fields.One2many('update.invoice.account.line.wiz', "update_invoice_id", "Update Account Line")
    

    def action_validate(self):
        check_update = False
        for line in self.update_invoice_line:
            if line.new_account_id.id:
                check_update = True
                line.aml_id.sudo().update({'account_id': line.new_account_id.id})

        if check_update:
            body = _('Updated GL Account by: ' + self.env.user.display_name)
            self.account_move_id.message_post(body=body)

class UpdateInvoiceAccountLineWiz(models.TransientModel):
    _name = 'update.invoice.account.line.wiz'

    update_invoice_id = fields.Many2one('update.invoice.account.wiz', "Update Account ID")
    aml_id = fields.Many2one('account.move.line', "AML ID")
    product_id = fields.Many2one('product.product', "Product")
    label = fields.Char(string="Label")
    account_id = fields.Many2one('account.account', "Account")
    new_account_id = fields.Many2one('account.account', "New Account")

    
