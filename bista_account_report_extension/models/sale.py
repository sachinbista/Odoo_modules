# -*- coding: utf-8 -*-

from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_type_lst = [
        ('Sales', 'Sales'),
        ('Replacement', 'Replacement'),
        ('Samples', 'Samples')
    ]

    order_type = fields.Selection(
        selection=order_type_lst,
        compute='compute_order_type',
        string='Order Type',
        default='Sales', store=True)

    def _prepare_invoice(self):
        """
        Override the original method to add 'order_type' to the invoice creation.
        """
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'order_type': self.order_type,
        })
        return res

    @api.depends('partner_id', 'name', 'order_line', 'order_line.product_template_id')
    def compute_order_type(self):
        for rec in self:
            order_type = 'Sales'
            partner_name = rec.partner_id and rec.partner_id.name or False
            if order_type == 'Sales' and partner_name:
                partner_name = partner_name.lower()
                if 'samples' in partner_name:
                    order_type = 'Samples'
                elif 'defect' in partner_name or 'replacement' in partner_name:
                    order_type = 'Replacement'
            order_name = rec.name or False
            if order_type == 'Sales' and order_name:
                order_name = order_name.lower()
                if 'samples' in order_name:
                    order_type = 'Samples'
                elif 'defect' in order_name or 'replacement' in order_name:
                    order_type = 'Replacement'
            if order_type == 'Sales' and rec.order_line:
                shipping_product = rec.order_line.filtered(
                    lambda il: il.product_template_id and il.product_template_id.id == 6200)
                if shipping_product and all(l.price_unit == 0 for l in rec.order_line.filtered(
                        lambda il: il.product_template_id and il.product_template_id.id != 6200)):
                    order_type = 'Replacement'
            rec.order_type = order_type
