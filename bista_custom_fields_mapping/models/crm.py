# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import fields, models, api

class Stage(models.Model):
    _inherit = "crm.stage"

    is_lost = fields.Boolean('Is Lost Stage?')

    @api.onchange('is_lost')
    def onchange_is_lost(self):
        if self.is_lost:
            self.is_won = False

    @api.onchange('is_won')
    def onchange_is_won(self):
        if self.is_won:
            self.is_lost = False