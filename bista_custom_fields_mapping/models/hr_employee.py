# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################

from odoo import fields, models, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sequence = fields.Integer(string="Sequence")