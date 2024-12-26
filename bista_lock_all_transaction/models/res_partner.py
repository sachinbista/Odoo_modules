# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    lock_all_transaction = fields.Boolean(string="Lock All Transaction",)


