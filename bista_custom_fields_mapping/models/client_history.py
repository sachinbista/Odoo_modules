# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################

from odoo import models,fields,api
import logging


_logger = logging.getLogger(__name__)

class ClientHistory(models.Model):
    _name = 'client.history'
    _description = 'Client History'

    _rec_name = 'sku'

    sale_date = fields.Date(string = 'Sale Date')
    sale_inv_number = fields.Char(string = 'Sale Inv #')
    sku = fields.Char(string='SKU # Sold')
    sku_desc = fields.Char(string='SKU Description')
    sale_price = fields.Float(string='Sale Price')
    cost_price = fields.Float(string='Cost Price')
    cat = fields.Many2one(string='Category',comodel_name='product.category')
    # cat = fields.Char(string='Category')
    qty = fields.Integer(string='QTY')
    vendor = fields.Many2one(string='Vendor',comodel_name='res.partner')
    vendor_style = fields.Char(string='Vendor Style #')

    partner_id = fields.Many2one(string='Customer',comodel_name='res.partner')
    hansa_customer = fields.Char(string='Hansa Customer', compute='_get_hansa_customer', store=True)
    hansa_email = fields.Char(string='Hansa Customer Email', compute='_get_hansa_customer', store=True)
    hansa_phone = fields.Char(string='Hansa Customer Phone', compute='_get_hansa_customer', store=True)
    hansa_address = fields.Char(string='Hansa Customer Address', compute='_get_hansa_customer', store=True)
    hansa_address_2 = fields.Char(string='Hansa Customer Address 2', compute='_get_hansa_customer', store=True)
    hansa_city = fields.Char(string='Hansa Customer City', compute='_get_hansa_customer', store=True)
    hansa_state = fields.Char(string='Hansa Customer State', compute='_get_hansa_customer', store=True)
    hansa_zip = fields.Char(string='Hansa Customer Zip', compute='_get_hansa_customer', store=True)

    @api.depends('sale_inv_number')
    def _get_hansa_customer(self):
        for res in self:
            hansa = self.env['original.client.history.records'].search([('sale_inv_number', '=', res.sale_inv_number)],
                                                                       limit=1)[0]
            res.hansa_customer = hansa.partner_id
            res.hansa_email = hansa.customer
            res.hansa_phone = hansa.phone
            res.hansa_address = hansa.street_address
            res.hansa_address_2 = hansa.street_2
            res.hansa_city = hansa.city
            res.hansa_state = hansa.state
            res.hansa_zip = hansa.zip


class OriginalClientHistoryRecords(models.Model):
    _name = 'original.client.history.records'
    _description = 'Hansa Clients History'

    sales_man = fields.Char(string='Sales Man')
    partner_id = fields.Char(string='Customer Name')
    street_address = fields.Char(string='Street Address')
    street_2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    zip = fields.Char(string='Zip')
    phone = fields.Char(string='Phone')
    customer = fields.Char(string='Customer Email')
    sale_date = fields.Date(string = 'Sale Date')
    sale_inv_number = fields.Char(string = 'Sale Inv #')
    sku = fields.Char(string='SKU # Sold')
    sku_desc = fields.Char(string='SKU Description')
    sale_price = fields.Float(string='Sale Price')
    cost_price = fields.Float(string='Cost Price')
    cat = fields.Char(string='Category')
    qty = fields.Integer(string='QTY')
    vendor = fields.Char(string='Vendor')
    vendor_style = fields.Char(string='Vendor Style #')

    synced = fields.Boolean(string='Imported',default=False)
    error = fields.Boolean(string='Error')
    odoo_partner_id = fields.Many2one(comodel_name='res.partner',string='Odoo Customer')

    note = fields.Text(string='Error Note')