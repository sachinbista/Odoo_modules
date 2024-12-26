    # -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    base_percentage = fields.Float('Base')
    goal_percentage = fields.Float('Goal')
    stretch_percentage = fields.Float('Stretch')
    short_code = fields.Char('Short Code')