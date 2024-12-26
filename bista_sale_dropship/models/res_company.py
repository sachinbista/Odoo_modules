# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = 'res.company'

    dropship_company_id = fields.Many2one('res.company',
        'Dropship Company')