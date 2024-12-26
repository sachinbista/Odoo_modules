# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    edi_uom_code = fields.Char(string="EDI UOM Code")
