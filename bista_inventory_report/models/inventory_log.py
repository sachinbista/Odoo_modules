# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models


class InventoryLogReport(models.Model):
    _name = "inventory.log.report"

    name = fields.Char(string="Name")
