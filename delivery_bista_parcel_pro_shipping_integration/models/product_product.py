# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, _, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    insured_value = fields.Float(string="Insured Value")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # insured_value = fields.Float(string="Insured Value", compute="_set_value",readonly=False)
    insured_value = fields.Float(
        'Insured Value', compute='_compute_insured_value',
        inverse='_set_value', store=True)

    @api.depends('product_variant_ids', 'product_variant_ids.insured_value')
    def _compute_insured_value(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.insured_value = template.product_variant_ids.insured_value
        for template in (self - unique_variants):
            template.insured_value = 0.0

    def _set_value(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.insured_value = template.insured_value