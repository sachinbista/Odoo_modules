##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    vendor_payment_terms_id = fields.Many2one('vendor.payment.terms',
                                              string="Vendor Payment Term")
