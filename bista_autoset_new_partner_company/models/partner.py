# -*- coding: utf-8 -*-
from odoo import api, models


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_get(self, fields_list):
        ret = super(Partner, self).default_get(fields_list)
        if self.env.user.active:
            ret.update({
                'company_id': self.env.company.id
            })
        return ret
