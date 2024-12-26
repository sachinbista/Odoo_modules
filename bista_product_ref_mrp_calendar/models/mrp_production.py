# -*- coding: utf-8 -*-
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
import datetime

from odoo import models, fields, api


class Production(models.Model):
    _inherit = 'mrp.production'

    product_ref = fields.Char(related="product_id.default_code")

