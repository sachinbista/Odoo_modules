# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_dropship = fields.Boolean(string="Is Dropship")
