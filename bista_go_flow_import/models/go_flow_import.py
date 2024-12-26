# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class GoFlowImport(models.Model):
    _name = "go.flow.import"

    is_process = fields.Boolean(string="Is Process", Default=False)
    order_number = fields.Char(string="Order Number")
    po_number = fields.Char(string="PO Number")
    order_id = fields.Char(string="Order ID")
    date = fields.Date(string="Date")
    status = fields.Char(string="status")
    tags = fields.Char(string="Tags")
    warehouse = fields.Char(string="Warehouse")
    store = fields.Char(string="Store")
    ship_by = fields.Char(string="Ship By")
    ship_date = fields.Date(string="Ship Date")
    subtotal = fields.Float(string="Subtotal")
    sales_tax = fields.Float(string="Sales Tax")
    shipping_charge = fields.Float(string="Shipping Charge")
    shipping_tax = fields.Float(string="Shipping Tax")
    discount = fields.Float(string="Discount")
    Total = fields.Float(string="Total")
    customer_name = fields.Char(string="Customer Name")
    customer_street = fields.Char(string="Customer Street")
    customer_street2 = fields.Char(string="Customer Street 2")
    customer_city = fields.Char(string="Customer City")
    customer_state = fields.Char(string="Customer State")
    customer_zip_code = fields.Char(string="Customer ZIP Code")
    customer_country = fields.Char(string="Customer Country")
    customer_phone = fields.Char(string="Customer Phone")
    customer_email = fields.Char(string="Customer Email")

    Carrier = fields.Char(string="Carrier")
    shipping_method = fields.Char(string="Shipping Method")
    scac = fields.Char(string="SCAC")
    tracking_numbers = fields.Char(string="Tracking Numbers")
    shipment_pounds = fields.Char(string="Shipment Pounds")
    shipment_ounces = fields.Char(string="Shipment Ounces")
    sale_order_id = fields.Many2one('sale.order', compute="_compute_sale_order_id", store=True)

    @api.depends('order_id')
    def _compute_sale_order_id(self):
        for rec in self:
            sale_order = self.env['sale.order'].search([('origin','=',rec.order_id),('state','!=','cancel')],limit=1)
            if sale_order:
                rec.sale_order_id = sale_order.id

    @api.model
    def create(self, vals):
        if 'order_id' in vals:
            exist = self.search([('order_id', '=', vals['order_id'])])
            if not exist:
                res = super(GoFlowImport, self).create(vals)
                return res
            return exist
        else:
            raise UserError('Order Id not found !!!')








