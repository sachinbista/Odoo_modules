# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """
    Inherit a Product Template"
    """
    _inherit = "product.template"

    markup = fields.Float(default=0)
    margin = fields.Float(default=0)
    total_lst_price = fields.Float(compute='_compute_lst_price', store=True)

    def _prepare_variant_values(self, combination):
        self.ensure_one()
        variant_values = super()._prepare_variant_values(combination)
        variant_values.update({
            'standard_price': self.standard_price,
            'markup': self.markup,
            'margin': self.margin,
        })
        return variant_values

    def _set_standard_price(self):
        for template in self:
            template.product_variant_ids.standard_price = template.standard_price

    @api.depends('standard_price', 'markup', 'margin')
    def _compute_lst_price(self):
        for record in self:
            total_lst_price = 0
            if 'only_calculate_margin' in self._context:
                margin = record.markup / (1 + record.markup/100)
                total_lst_price = record.standard_price + (record.standard_price * record.markup/100)
                record.update({
                    'margin': margin,
                    'list_price':total_lst_price,
                    'total_lst_price': total_lst_price
                    })
            elif 'only_calculate_markup' in self._context:
                markup = record.margin / (1 - record.margin/100)
                total_lst_price = record.standard_price + (record.standard_price * markup/100)
                record.update({
                    'markup': markup,
                    'list_price': total_lst_price,
                    'total_lst_price': total_lst_price
                    })
            else:
                if record.standard_price:
                    total_lst_price = record.standard_price + (record.standard_price * record.markup/100)
                    record.update({
                        'total_lst_price': total_lst_price,
                        'list_price': total_lst_price
                        })
            if record.product_variant_ids and len(record.product_variant_ids) == 1:
                record.product_variant_ids.update({
                    'margin': record.margin,
                    'markup': record.markup,
                    'lst_price': total_lst_price
                })


class Product(models.Model):
    _inherit = 'product.product'

    def _compute_list_price(self):
        uom_model = self.env["uom.uom"]
        for product in self:
            price = product.lst_price or product.product_tmpl_id.list_price
            if "uom" in self.env.context:
                price = product.uom_id._compute_price(
                    price, uom_model.browse(self.env.context["uom"])
                )
            product.list_price = price

    @api.depends('list_price', 'price_extra', 'standard_price', 'markup', 'margin')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        super()._compute_product_lst_price()
        for record in self:
            if 'only_calculate_margin' in self._context:
                margin = record.markup / (1 + record.markup / 100)
                total_lst_price = record.standard_price + (record.standard_price * record.markup / 100) + record.price_extra
                record.with_context({'noupdate_varinat_list_price': True}).update({
                    'margin': margin,
                    'lst_price': total_lst_price
                })
            elif 'only_calculate_markup' in self._context:
                markup = record.margin / (1 - record.margin / 100)
                total_lst_price = record.standard_price + (record.standard_price * markup / 100) + record.price_extra
                record.with_context({'noupdate_varinat_list_price': True}).update({
                    'markup': markup,
                    'lst_price': total_lst_price
                })
            else:
                if record.standard_price:
                    total_lst_price = record.standard_price + (record.standard_price * record.markup / 100) + record.price_extra
                    record.with_context({'noupdate_varinat_list_price': True}).update({
                        'lst_price': total_lst_price,
                    })
                else:
                    record.with_context({'noupdate_varinat_list_price': True}).update({
                        'lst_price': record.product_tmpl_id.total_lst_price,
                    })

    @api.onchange('lst_price')
    def _set_product_lst_price(self):
        if 'noupdate_varinat_list_price' not in self._context:
            super()._set_product_lst_price()

    markup = fields.Float()
    margin = fields.Float('Gross Margin %')
    list_price = fields.Float(
        compute="_compute_list_price",
    )
    lst_price = fields.Float(store=True)