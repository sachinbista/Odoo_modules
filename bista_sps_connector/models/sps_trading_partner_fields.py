# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import fields, models


class SpsTradingPartnerFields(models.Model):
    _rec_name = 'trading_partner_field'
    _name = "sps.trading.partner.fields"

    trading_partner_field = fields.Char(string='SPS Field Name')
    partner_id = fields.Many2one('res.partner', string='Trading PartnerId')
    document_type = fields.Selection([('order_document', 'Order Document'), ('order_ack', 'Order Ack Document'),
                                      ('shipment_ack', 'Shipment Ack Document'),('invoice_ack', 'Invoice Ack Document')],
                              string='Document Type')