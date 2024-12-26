# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields
from odoo.exceptions import ValidationError

import requests
import re


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SaleOrder, self).create(vals_list)
        for partner in records.mapped('partner_id'):
            partner.customer_rank = partner.customer_rank + 1
        return records
