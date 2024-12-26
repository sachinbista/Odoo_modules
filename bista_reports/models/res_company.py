# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, api



class ResCompany(models.Model):
    _inherit = 'res.company'


    contact_us_email = fields.Char(string="Contact Us Email")