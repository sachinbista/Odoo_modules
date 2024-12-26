from odoo import models, fields, api, _


class ShippingCharge(models.Model):
    _name = 'shipping.charge'
    _description = 'Shipping Charge'

    name = fields.Char(string='Name')
    # company_id = fields.Many2one('res.company',string='Company')
    country_id = fields.Many2one('res.country',string='Country')
    shipping_charge_line_ids = fields.One2many('shipping.charge.line','shipping_charge_id',
                                               string='Shipping Charge Line',oncascade='delete')


class ShippingChargeLine(models.Model):
    _name = "shipping.charge.line"
    _description = 'Shipping Charge Line'

    shipping_charge_id = fields.Many2one('shipping.charge',string='Shipping Charge')
    from_qty = fields.Float(string='From Qty')
    to_qty = fields.Float(string='To Qty')
    price = fields.Float(string='Price')
