# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    users_count = fields.Integer(compute='_compute_user_count', store=True)

    @api.depends('user_id', 'other_users')
    def _compute_user_count(self):
        for rec in self:
            if rec.other_users or rec.user_id:
                rec.users_count = len(rec.other_users.filtered(lambda x: x.active == True)) + len(rec.user_id)
