# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields
from odoo.exceptions import ValidationError

import requests
import re


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PurchaseOrder, self).create(vals_list)
        for partner in records.mapped('partner_id'):
            partner.supplier_rank = partner.supplier_rank + 1
        return records
