##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    address = fields.Boolean("One Time")
    customer_name = fields.Char("Name")
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    zip = fields.Char('Zip')
    state_id = fields.Many2one(
        "res.country.state", string='State',
        domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one(
        'res.country', string='Country')

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.order_line.filtered(lambda x: x.is_delivery):
                raise ValidationError(
                    _('The sale order must have at least one line with a shipping method.'))
        return res

    @api.model_create_multi
    def create(self, values_list):
        for vals in values_list:
            if 'address' in vals and vals.get('address') and vals.get(
                    'partner_id'):
                if (vals.get('customer_name') or vals.get('street') or
                        vals.get('street2') or vals.get('city') or
                        vals.get('zip') or vals.get('state_id') or
                        vals.get('country_id')):
                    contact = self.env['res.partner'].search([
                        ('parent_id', '=', vals.get('partner_id')),
                        ('is_one_time_add', '=', True),
                        ('active', '=', False)], limit=1)
                    var = {
                        'name': vals.get('customer_name'),
                        'street': vals.get('street') or '',
                        'street2': vals.get('street2') or '',
                        'city': vals.get('city') or '',
                        'zip': vals.get('zip') or '',
                        'state_id': vals.get('state_id') or False,
                        'country_id': vals.get('country_id') or False,
                        'type': 'delivery',
                        'is_one_time_add': True,
                        'active': False,
                        'parent_id': vals.get('partner_id')
                    }
                    if contact:
                        contact.write(var)
                        if (vals.get('partner_shipping_id') and
                                vals.get('partner_shipping_id') != contact.id):
                            vals.update({'partner_shipping_id': contact.id})
                    else:
                        contact = self.env['res.partner'].create(var)
                        if (vals.get('partner_shipping_id') and
                                vals.get('partner_shipping_id') != contact.id):
                            vals.update({'partner_shipping_id': contact.id})
        return super(SaleOrder, self).create(values_list)

    def write(self, values):
        result = super(SaleOrder, self).write(values)
        for each in self:
            if each.address and each.partner_id:
                if (values.get('customer_name') or values.get('street') or
                        values.get('street2') or values.get('city') or
                        values.get('zip') or values.get('state_id') or
                        values.get('country_id')):
                    customer_name = values.get('customer_name') if values.get(
                        'customer_name') else each.customer_name or ''
                    street = values.get('street') if values.get('street') \
                        else each.street or ''
                    street2 = values.get('street2') if values.get('street2') \
                        else each.street2 or ''
                    city = values.get('city') if values.get('city') \
                        else each.city
                    zip = values.get('zip') if values.get('zip') \
                        else each.zip
                    state_id = values.get('state_id') if values.get('state_id') \
                        else each.state_id and each.state_id.id or False
                    country_id = values.get('country_id') if values.get(
                        'country_id') \
                        else each.country_id and each.country_id.id or False

                    contact = self.env['res.partner'].search([
                        ('parent_id', '=', each.partner_id.id),
                        ('is_one_time_add', '=', True),
                        ('active', '=', False)], limit=1)
                    var = {
                        'name': customer_name,
                        'street': street,
                        'street2': street2,
                        'city': city,
                        'zip': zip,
                        'state_id': state_id,
                        'country_id': country_id,
                        'type': 'delivery',
                        'is_one_time_add': True,
                        'active': False,
                        'parent_id': each.partner_id.id
                    }
                    if contact:
                        contact.write(var)
                        if (each.partner_shipping_id and
                                each.partner_shipping_id.id != contact.id):
                            each.partner_shipping_id = contact.id
                    else:
                        contact = self.env['res.partner'].create(var)
                        if (each.partner_shipping_id and
                                each.partner_shipping_id.id != contact.id):
                            each.partner_shipping_id = contact.id
        return result


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_one_time_add = fields.Boolean("Is One Time Address")


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    display_price = fields.Float(string='Cost', readonly=False)
