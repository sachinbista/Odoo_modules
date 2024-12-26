# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields
from odoo.exceptions import ValidationError

import requests
import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AccountMove, self).create(vals_list)
        for record in records:
            partner_id = record.partner_id
            if partner_id and record.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                partner_id.customer_rank = partner_id.customer_rank + 1
            if partner_id and record.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                partner_id.supplier_rank = partner_id.supplier_rank + 1
        return records
