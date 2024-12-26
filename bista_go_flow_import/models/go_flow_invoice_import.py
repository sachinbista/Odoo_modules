# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class QuickbookInvoiceImport(models.Model):
    _name = "quickbook.invoice"
    _description = 'Goflow Invoice Import'


    invoice_type = fields.Char(string="Type")
    invoice_date = fields.Date(string="Date")
    ship_date = fields.Date(string="Ship Date")
    invoice_via = fields.Char(string="Via")
    invoice_num = fields.Char(string="Num")
    invoice_po = fields.Char(string="P.O.#")
    name = fields.Char(string="Name")
    invoice_memo = fields.Char(string="Memo")
    invoice_payment_term = fields.Char(string="Terms")
    invoice_item = fields.Char(string="Item")
    invoice_item_des = fields.Char(string="Item Description")
    invoice_cls = fields.Char(string="Class")
    invoice_clr = fields.Char(string="Clr")
    invoice_split = fields.Char(string="Split")
    qty = fields.Float(string="Qty")
    sales_price = fields.Float(string="Sale Price")
    debit = fields.Float(string="Debit")
    credit = fields.Float(string="Credit")
    balance = fields.Float(string="Balance")
    invoice_so = fields.Float(string="S.O.#")

    @api.model
    def create(self, vals):
        if 'invoice_date' in vals and 'invoice_num' in vals and 'name' in vals and 'invoice_po' in vals and 'invoice_item' in vals:
            exist = self.search([('invoice_date', '=', vals['invoice_date']),('invoice_num', '=', vals['invoice_num']),('name', '=', vals['name']),('invoice_po', '=', vals['invoice_po']),('invoice_item', '=', vals['invoice_item'])])
            if not exist:
                res = super(QuickbookInvoiceImport, self).create(vals)
                return res
            return exist
        else:
            raise UserError('Order Id not found !!!')

