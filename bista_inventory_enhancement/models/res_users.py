# -*- coding: utf-8 -*-

from odoo import api, fields, models



class ResUsers(models.Model):
    _inherit = 'res.users'

    _sql_constraints = [
        ('pin_password_uniq', 'UNIQUE (pin_password)', 'The PIN Password must be unique!'),
    ]


    pin_password = fields.Char("PIN Password")