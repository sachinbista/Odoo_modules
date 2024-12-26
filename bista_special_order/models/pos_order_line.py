# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from functools import partial

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError,UserError



class PosOrderLine(models.Model):
    _inherit = "pos.order.line"


    is_special = fields.Boolean("Is Special",readonly=False)



    def _export_for_ui(self, orderline):
        res = super(PosOrderLine, self)._export_for_ui(orderline)
        res.update({
            'is_special': orderline.is_special if orderline else ''
            })
        return res
