# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    part_no_ids = fields.One2many('product.alias.part.number', 'product_template_id',
                                  string="Product Alias Part Numbers")

    @api.onchange('part_no_ids')
    def _onchange_customer_id(self):
        repeat_list = []
        for rec in self.part_no_ids:
            if rec.customer_id:
                if rec.customer_id.id not in repeat_list:
                    repeat_list.append(rec.customer_id.id)
                elif rec.customer_id.id in repeat_list:
                    raise ValidationError("You can not add same customer")

    @api.depends('part_no_ids')
    def _compute_default_alias_detail(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code
            values = {'part_no_ids': template.part_no_ids}
            template.product_variant_ids.write(values)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    part_no_ids = fields.One2many('product.alias.part.number', 'product_id', string="Product Alias Part Numbers")

    @api.onchange('part_no_ids')
    def _onchange_customer_id(self):
        repeat_list = []
        for rec in self.part_no_ids:
            if rec.customer_id:
                if rec.customer_id.id not in repeat_list:
                    repeat_list.append(rec.customer_id.id)
                elif rec.customer_id.id in repeat_list:
                    raise ValidationError("You can not add same customer")


class ProductAliasPartNumber(models.Model):
    _name = 'product.alias.part.number'
    _rec_name = 'part_no'

    part_no = fields.Char(string="Part Number")
    product_template_id = fields.Many2one('product.template', string="Product Template", ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product Product", ondelete='cascade')
    customer_id = fields.Many2one('res.partner', string="Customer", domain="[('parent_id', '=', False)]")

    _sql_constraints = [('part_no_unique', 'UNIQUE(part_no)', 'Part Number should be unique')]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_template_id = self.product_id.product_tmpl_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_template_id'):
                product = self.env['product.template'].browse(vals.get('product_template_id'))
                vals.update({'product_id': product.product_variant_id.id})
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals.get('product_id'))
                vals.update({'product_template_id': product.product_tmpl_id.id})
        return super(ProductAliasPartNumber, self).create(vals_list)

    @api.constrains('product_id', 'customer_id')
    def _check_unique_part_no(self):
        for rec in self:
            duplicate_records_for_part = self.search([
                ('product_id', '=', rec.product_id.id),
                ('customer_id', '=', rec.customer_id.id),
                ('id', '!=', rec.id)
            ])
            if duplicate_records_for_part:
                raise ValidationError(
                    _("You can not create more then one part number for same customer with same product"))
