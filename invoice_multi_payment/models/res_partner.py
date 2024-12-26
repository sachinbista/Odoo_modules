# -*- coding: utf-8 -*-
from lxml import etree

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, Warning, MissingError
from odoo.fields import Many2one


class ResPartner(models.Model):
    _inherit = 'res.partner'

    branch_id = fields.Many2one('res.branch', string="Branch", required=True, ondelete='restrict')