# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FlaskServerConfig(models.Model):
    _name = 'flask.server.config'
    _description = 'Flask Server Configuration'

    name = fields.Char("Name", required=True)
    url = fields.Char("URL", required=True)
    auth_token = fields.Char("Auth Token", required=True)
    active = fields.Boolean("Active", default=True)

    def update_active_status(self):
        self.active = not self.active
        active_roasters = self.search_count([('active', '=', True)])
        if active_roasters > 1:
            raise UserError("Only one roaster configuration can be active at a time")

