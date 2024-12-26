# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'ResPartner'

    is_sale_ref = fields.Boolean(string="Is Sales Rep?")
    sale_ref_id = fields.Many2one('res.partner', string="Sales Rep", domain=[('is_sale_ref', '=', True)])
