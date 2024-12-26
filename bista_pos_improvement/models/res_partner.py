# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, _, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create_from_ui(self, partner):
        res = super(ResPartner, self).create_from_ui(partner=partner)
        if res:
            partner = self.browse(res)
            partner.write({'company_id':self.env.company.id})
        return res

