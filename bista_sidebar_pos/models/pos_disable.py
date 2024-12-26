# -*- coding: utf-8 -*-
# Part of Bistasolutions. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_allow_sidebar = fields.Boolean("Allow Sidebar")

    @api.onchange('is_allow_sidebar')
    def onchange_sidebar_settings(self):
        for user in self.with_context(active_test=False):
            user.employee_id.update({
                'is_allow_sidebar': user.is_allow_sidebar,
            })

    def action_create_employee(self):
        self.ensure_one()
        res = super(ResUsers, self).action_create_employee()
        for user in self:
            user.employee_id.update({
                'is_allow_sidebar': user.is_allow_sidebar
            })


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    is_allow_sidebar = fields.Boolean("Allow Sidebar")
