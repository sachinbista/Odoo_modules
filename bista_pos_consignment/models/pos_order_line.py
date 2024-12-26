# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from functools import partial

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError,UserError



class PosOrderLine(models.Model):
    _inherit = "pos.order.line"


    consignment_move = fields.Boolean("Consignment Move",readonly=False)