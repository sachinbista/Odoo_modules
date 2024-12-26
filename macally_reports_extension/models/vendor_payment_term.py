##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, _


class VendorPaymentTerms(models.Model):
    _name = "vendor.payment.terms"
    _description = "Vendor Payment Terms"

    name = fields.Char("Name")


class ShipVia(models.Model):
    _name = "ship.via"
    _description = "Ship Via"

    name = fields.Char("Name")
