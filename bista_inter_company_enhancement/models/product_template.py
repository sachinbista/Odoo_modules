# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'product template'

    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')],
        string="Tracking", required=False, default='none',
        compute='_compute_tracking', store=True, readonly=False, precompute=True,
        company_dependent=True,
        help="Ensure the traceability of a storable product in your warehouse.")
