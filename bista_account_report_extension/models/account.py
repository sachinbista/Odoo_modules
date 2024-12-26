# -*- coding: utf-8 -*-

from odoo import models, api, fields


class AccountReport(models.Model):
    _inherit = "account.report"

    exclude_aging = fields.Boolean(string='Exclude in Aging')


class AccountMove(models.Model):
    _inherit = 'account.move'

    order_type_lst = [
        ('Sales', 'Sales'),
        ('Replacement', 'Replacement'),
        ('Samples', 'Samples')
    ]

    order_type = fields.Selection(
        selection=order_type_lst,
        string='Order Type',
        default='Sales')
    exclude_aging = fields.Boolean(compute='get_exclude_aging', string='Exclude Aging', store=True)

    @api.depends('invoice_line_ids', 'invoice_line_ids.price_unit')
    def get_exclude_aging(self):
        for rec in self:
            exclude_aging = False
            if all(l.price_unit == 0 for l in rec.invoice_line_ids.filtered(
                    lambda il: il.account_id and il.account_id.id != 1308)):
                exclude_aging = True
            rec.exclude_aging = exclude_aging
