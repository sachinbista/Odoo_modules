# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, api, fields
from odoo.osv import expression

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    source_reference = fields.Char(
        'Source Ref', compute="compute_source_reference", copy=False)

    @api.depends('move_id', 'account_id', 'journal_id')
    def compute_source_reference(self):
        for move_line in self:
            source_reference = False
            if move_line.journal_id.name in ['Customer Invoices', 'Vendor Bills']:
                source_reference = move_line.move_id.invoice_origin or False
            elif move_line.journal_id.name == 'Inventory Valuation':
                source_reference = move_line.move_id.stock_move_id.origin or False
            move_line.source_reference = source_reference

