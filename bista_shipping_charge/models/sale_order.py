from itertools import product
from odoo.exceptions import UserError
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_delivery_wizard(self):
        """Open the delivery wizard to add a shipping charge line."""
        shipping_charge_id = self.env['shipping.charge'].search([('country_id','=',self.company_id.country_id.id)],limit=1)
        if not shipping_charge_id:
            return
        product_id = self.env['product.product'].search([
            ('detailed_type', '=', 'service'),
            ('sale_ok','=',False),('purchase_ok','=',False),
            ('invoice_policy','=','order')], limit=1)
        if not product_id:
            raise UserError(_('Please define some service product, as delivery method.'))
        price_unit = self._calculate_shipping_charge(shipping_charge_id)
        values = self._prepare_shipping_charge_vals(product_id, price_unit)
        return self.env['sale.order.line'].sudo().create(values)

    def _calculate_shipping_charge(self, shipping_charge_id):
        """Calculate the shipping charge based on the order quantity."""
        quantity = sum(line.product_uom_qty for line in self.order_line if not line.is_delivery)
        line = shipping_charge_id.shipping_charge_line_ids.filtered(
            lambda l: l.from_qty <= quantity <= l.to_qty
        )
        price = line.price if line else 0.0
        self.order_line.filtered(lambda l: l.is_delivery).unlink()
        return price

    def _prepare_shipping_charge_vals(self, product_id, price_unit):
        context = {}
        if self.partner_id:
            # set delivery detail in the customer language
            context['lang'] = self.partner_id.lang
            # carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = product_id.taxes_id._filter_taxes_by_company(self.company_id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        # Create the sales order line

        if product_id.description_sale:
            so_description = '%s: %s' % (product_id.name,
                                        product_id.product_id.description_sale)
        else:
            so_description = product_id.name
        values = {
            'order_id': self.id,
            'name': so_description,
            'price_unit': price_unit,
            'product_uom_qty': 1,
            'product_uom': product_id.uom_id.id,
            'product_id': product_id.id,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        # if carrier.free_over and self.currency_id.is_zero(price_unit) :
        #     values['name'] += '\n' + _('Free Shipping')
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        del context
        return values
