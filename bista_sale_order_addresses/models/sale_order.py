# -*- coding: utf-8 -*-
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
import datetime

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_street = fields.Char(related="partner_id.street", readonly=False)
    partner_street2 = fields.Char(related="partner_id.street2", readonly=False)
    partner_city = fields.Char(related="partner_id.city", readonly=False)
    partner_zip = fields.Char(related="partner_id.zip", readonly=False)
    partner_state_id = fields.Many2one('res.country.state', related="partner_id.state_id", readonly=False)
    partner_country_id = fields.Many2one('res.country', related="partner_id.country_id", readonly=False)
    partner_shipping_street = fields.Char(related="partner_shipping_id.street", string="Shipping Street", readonly=False)
    partner_shipping_street2 = fields.Char(related="partner_shipping_id.street2", string="Shipping Street 2", readonly=False)
    partner_shipping_city = fields.Char(related="partner_shipping_id.city", string="Shipping City", readonly=False)
    partner_shipping_zip = fields.Char(related="partner_shipping_id.zip", string="Shipping Zip", readonly=False)
    partner_shipping_state_id = fields.Many2one('res.country.state', related="partner_shipping_id.state_id",
                                                string="Shipping State", readonly=False)
    partner_shipping_country_id = fields.Many2one('res.country', related="partner_shipping_id.country_id",
                                                  string="Shipping Country", readonly=False)
    partner_invoice_street = fields.Char(related="partner_invoice_id.street", string="Billing Street", readonly=False)
    partner_invoice_street2 = fields.Char(related="partner_invoice_id.street2", string="Billing Street 2", readonly=False)
    partner_invoice_city = fields.Char(related="partner_invoice_id.city", string="Billing City", readonly=False)
    partner_invoice_zip = fields.Char(related="partner_invoice_id.zip", string="billing Zip", readonly=False)
    partner_invoice_state_id = fields.Many2one('res.country.state', related="partner_invoice_id.state_id",
                                               string="Billing State", readonly=False)
    partner_invoice_country_id = fields.Many2one('res.country', related="partner_invoice_id.country_id",
                                                 string="Billing Country", readonly=False)
