# -*- coding:utf-8 -*-

from odoo import api, models, fields



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_sale_order_details(self,picking):
        return self.env['sale.order'].search([('name', '=', picking.origin)])

    def get_partner_address_invoice_id(self,picking):
        addresses = picking.partner_id.address_get(['invoice'])
        invoice_id = picking.env['res.partner'].browse(addresses['invoice'])
        return invoice_id

    def get_partner_address_shipping_id(self,picking):
        addresses = picking.partner_id.address_get(['delivery'])
        shipping_id = picking.env['res.partner'].browse(addresses['delivery'])
        return shipping_id

    def product_from_sale_lines(self,sale_order_id, product):
        for line in sale_order_id.order_line:
            if line.product_id == product:
                return line

    def get_name(self,name):
        return name.replace("WH/OUT/", "").replace("WH/IN/", "").replace("CHIC1/OUT/", "")