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
    sale_ref_readonly = fields.Boolean(string='Sale Ref Readonly', compute='_compute_sale_ref_readonly')

    @api.depends('user_id')
    def _compute_sale_ref_readonly(self):
        for order in self:
            order.sale_ref_readonly = not self.env.user.has_group('sales_team.group_sale_manager')

