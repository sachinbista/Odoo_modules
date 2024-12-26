# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # def _generate_invoice(self, picking=None):
    #     if picking.carrier_id or picking.carrier_tracking_ref:
    #         return super(SaleOrder, self)._generate_invoice(picking)
    #     return
