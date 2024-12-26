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
    _description = 'res partner'

    picking_notes = fields.Text(string="Picking Notes")
    is_automatically_created = fields.Boolean(
        string='Is Automatically Created?', default=False)

    @api.model
    def create(self, vals):
        if self.env.context.get('import_file'):
            vals['is_automatically_created'] = True
        return super(ResPartner, self).create(vals)
