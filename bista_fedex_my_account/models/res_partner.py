# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_fedex_carrier_account = fields.Char(string='FEDEX Account Number', company_dependent=True)
    fedex_bill_my_account = fields.Boolean(related='property_delivery_carrier_id.fedex_bill_my_account')

    # @api.model
    # def create(self, vals):
    #     if vals and vals.get('type') == 'delivery':
    #         vals['phone'] = '800-505-2078'
    #     return super(ResPartner, self).create(vals)
    #
    # def update_delivery_phone(self):
    #     partner_ids = self.search([('type', '=', 'delivery')])
    #     print("\n\n\npartner_ids", partner_ids)
    #     self._cr.execute("""UPDATE res_partner
    #                                 SET phone=%s
    #                                 WHERE id IN %s""", ('800-505-2078', tuple(partner_ids.ids)))