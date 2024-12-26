# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.bus.models.bus_presence import AWAY_TIMER
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER


class ResUsers(models.Model):

    _inherit = "res.users"


    def _is_system(self):
        res = super()._is_system()
        self.ensure_one()
        res = self.has_group('account.group_account_manager') or self.has_group('base.group_system')
        return res