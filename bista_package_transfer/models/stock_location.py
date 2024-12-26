# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class Location(models.Model):
    _inherit = 'stock.location'

    single_package_allowed = fields.Boolean('Single Package Allowed', copy=False,
                                            readonly=False, store=True)
