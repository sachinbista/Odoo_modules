# -*- coding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2013-Today Globalteckz (http://www.globalteckz.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import itertools
import logging

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.osv import expression

class ProductAutoSku(models.Model):
    _name = 'product.auto.sku'
    _description = 'Auto Sku Creation'
    _rec_name = 'pro_name'

    pro_name = fields.Char(string='Name')
    sku_by_supplier = fields.Selection([('first_two', 'FIRST TWO LETTERS'), ('define_supp', 'DEFINE ON SUPPLIER')],
                                       string='Supplier')
    sku_by_product = fields.Selection([('first_four', 'First Four Digit Of Internal Category') ,('short_code','Short Code of Internal Category') ], string='Product')
    sku_by_attribute = fields.Selection([('one_latter', 'FIRST LETTER'), ('three_latter', 'FIRST THREE LETTERS')],string='Attributes Options')
    sequence = fields.Selection([('one', '01'),
                                 ('two', '001'), ('three', '0001'), ('four', '00001'), ('five', '000001'),
                                 ('six', '0000001'), ('seven', '00000001'), ('eight', '000000001'),
                                 ('nine', '0000000001'), ('ten', '00000000001')], string='Sequence')
    hyphens = fields.Boolean(string='Use Period')
    enable = fields.Boolean(string='Enable Auto Sku Generation')

    # service_product_apply = fields.Boolean(string='Apply On Service Type of Product')

    # @api.multi
    def re_generate_sku(self):
        "Function Started"
        product_obj = self.env['product.product']
        product_sku_obj = self.env['product.auto.sku']
        product_id = product_obj.search([('default_code', '=', False)])
        for res in product_id:
            if res.name:
                sku_info_id = product_sku_obj.search([])
                seq_id = self.env['ir.sequence'].search([('name', 'ilike', 'Product Sequence')])
                if sku_info_id.enable == True:
                    if sku_info_id.sequence == 'one':
                        seq_id.write({'padding': 2})
                    if sku_info_id.sequence == 'two':
                        seq_id.write({'padding': 3})
                    if sku_info_id.sequence == 'three':
                        seq_id.write({'padding': 4})
                    if sku_info_id.sequence == 'four':
                        seq_id.write({'padding': 5})
                    if sku_info_id.sequence == 'five':
                        seq_id.write({'padding': 6})
                    if sku_info_id.sequence == 'six':
                        seq_id.write({'padding': 7})
                    if sku_info_id.sequence == 'seven':
                        seq_id.write({'padding': 8})
                    if sku_info_id.sequence == 'eight':
                        seq_id.write({'padding': 9})
                    if sku_info_id.sequence == 'nine':
                        seq_id.write({'padding': 10})
                    if sku_info_id.sequence == 'ten':
                        seq_id.write({'padding': 11})
                    if res:
                        res.update({'pro_sequence': self.env['ir.sequence'].next_by_code('product.sequence')})
                    supplier_name = ''
                    sku_hyphens = ''
                    sort_pro_name = ''
                    value = ''
                    sku_n = ''
                    sku_m = ''
                    sku = ''
                    if sku_info_id.sku_by_supplier == 'first_two':
                        for supplier in res.seller_ids:
                            part_name = supplier[0].partner_id
                            supplier_name = part_name.name[:2].upper()
                    if sku_info_id.sku_by_supplier == 'define_supp':
                        for supplier in res.seller_ids:
                            part_name = supplier[0].partner_id
                            supplier_name = part_name.short_name
                    if sku_info_id.sku_by_product == 'first_four':
                        product_name = res.categ_id.name
                        sort_pro_name = product_name[:4].upper()

                    if sku_info_id.sku_by_product == 'short_code':
                        product_name = res.categ_id.short_code if res.categ_id.short_code else ''
                        sort_pro_name = product_name
                    if sku_info_id.sku_by_attribute == 'three_latter':
                        if res.product_template_attribute_value_ids:
                            for att_value in res.product_template_attribute_value_ids:
                                if sku_info_id.hyphens == True:
                                    value = value + str(att_value.name[:3] + '.').upper()
                                else:
                                    value = value + str(att_value.name[:3]).upper()
                    if sku_info_id.sku_by_attribute == 'one_latter':
                        if res.product_template_attribute_value_ids:
                            for att_value in res.product_template_attribute_value_ids:
                                if sku_info_id.hyphens == True:
                                    value = value + str(att_value.name[:1] + '.').upper()
                                else:
                                    value = value + str(att_value.name[:1]).upper()
                    if sku_info_id.hyphens == True:
                        sku_hyphens = '.'
                        if str(supplier_name) != '':
                            sku_n = str(supplier_name) + str(sku_hyphens).upper()
                        if str(sort_pro_name) != '':
                            sku_m = sku_n + str(sort_pro_name) + str(sku_hyphens).upper()
                        if str(value) != '':
                            sku = sku_m + str(value) + str(res.pro_sequence)
                        else:
                            sku = sku_m + str(res.pro_sequence)
                    else:
                        sku = str(supplier_name) + str(sort_pro_name) + str(value) + str(res.pro_sequence)
                    res.write({'default_code': sku})
        return True

    # @api.multi
    def re_generate_sku_all(self):
        "Function Started"
        product_obj = self.env['product.product']
        product_sku_obj = self.env['product.auto.sku']
        product_id = product_obj.search([])
        for res in product_id:
            if res.name:
                sku_info_id = product_sku_obj.search([])
                seq_id = self.env['ir.sequence'].search([('name', 'ilike', 'Product Sequence')])
                if sku_info_id.enable == True:
                    if sku_info_id.sequence == 'one':
                        seq_id.write({'padding': 2})
                    if sku_info_id.sequence == 'two':
                        seq_id.write({'padding': 3})
                    if sku_info_id.sequence == 'three':
                        seq_id.write({'padding': 4})
                    if sku_info_id.sequence == 'four':
                        seq_id.write({'padding': 5})
                    if sku_info_id.sequence == 'five':
                        seq_id.write({'padding': 6})
                    if sku_info_id.sequence == 'six':
                        seq_id.write({'padding': 7})
                    if sku_info_id.sequence == 'seven':
                        seq_id.write({'padding': 8})
                    if sku_info_id.sequence == 'eight':
                        seq_id.write({'padding': 9})
                    if sku_info_id.sequence == 'nine':
                        seq_id.write({'padding': 10})
                    if sku_info_id.sequence == 'ten':
                        seq_id.write({'padding': 11})
                    if res:
                        res.update({'pro_sequence': self.env['ir.sequence'].next_by_code('product.sequence')})
                    supplier_name = ''
                    sku_hyphens = ''
                    sort_pro_name = ''
                    value = ''
                    sku_n = ''
                    sku_m = ''
                    sku = ''
                    if sku_info_id.sku_by_supplier == 'first_two':
                        for supplier in res.seller_ids:
                            part_name = supplier[0].partner_id
                            supplier_name = part_name.name[:2].upper()
                    if sku_info_id.sku_by_supplier == 'define_supp':
                        for supplier in res.seller_ids:
                            part_name = supplier[0].partner_id
                            if part_name != False:
                                supplier_name = part_name.short_name
                    if sku_info_id.sku_by_product == 'first_four':
                        product_name = res.categ_id.name
                        sort_pro_name = product_name[:4].upper()

                    if sku_info_id.sku_by_product == 'short_code':
                        product_name = res.categ_id.short_code if res.categ_id.short_code else ''
                        sort_pro_name = product_name

                    if sku_info_id.sku_by_attribute == 'three_latter':
                        if res.product_template_attribute_value_ids:
                            for att_value in res.product_template_attribute_value_ids:
                                if sku_info_id.hyphens == True:
                                    value = value + str(att_value.name[:3] + '.').upper()
                                else:
                                    value = value + str(att_value.name[:3]).upper()
                    if sku_info_id.sku_by_attribute == 'one_latter':
                        if res.product_template_attribute_value_ids:
                            for att_value in res.product_template_attribute_value_ids:
                                if sku_info_id.hyphens == True:
                                    value = value + str(att_value.name[:1] + '.').upper()
                                else:
                                    value = value + str(att_value.name[:1]).upper()
                    if sku_info_id.hyphens == True:
                        sku_hyphens = '.'
                        if str(supplier_name) != '':
                            sku_n = str(supplier_name) + str(sku_hyphens)
                        if str(sort_pro_name) != '':
                            sku_m = sku_n + str(sort_pro_name) + str(sku_hyphens)
                        if str(value) != '':
                            sku = sku_m + str(value) + str(res.pro_sequence)
                        else:
                            sku = sku_m + str(res.pro_sequence)
                    else:
                        sku = str(supplier_name) + str(sort_pro_name) + str(value) + str(res.pro_sequence)
                    res.write({'default_code': sku})
        return True


class ResPartner(models.Model):
    _inherit = 'res.partner'

    short_name = fields.Char(string='Vendor Short Name')

class ProductProduct(models.Model):
    _inherit = 'product.product'

    pro_sequence = fields.Char(string='Product Sequence')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pro_sequence = fields.Char(string='Product Sequence')

    def _create_variant_ids(self):
        self.env.flush_all()
        super()._create_variant_ids()
        Product = self.env["product.product"]

        variants_to_create = []
        variants_to_activate = Product
        variants_to_unlink = Product

        for tmpl_id in self:
            lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted(lambda p: (p.active, -p.id))

            current_variants_to_create = []
            current_variants_to_activate = Product

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            single_value_lines = lines_without_no_variants.filtered(lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
            if single_value_lines:
                for variant in all_variants:
                    combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
                    # Do not add single value if the resulting combination would
                    # be invalid anyway.
                    if (
                        len(combination) == len(lines_without_no_variants) and
                        combination.attribute_line_id == lines_without_no_variants
                    ):
                        variant.product_template_attribute_value_ids = combination

            # Set containing existing `product.template.attribute.value` combination
            existing_variants = {
                variant.product_template_attribute_value_ids: variant for variant in all_variants
            }

            # Determine which product variants need to be created based on the attribute
            # configuration. If any attribute is set to generate variants dynamically, skip the
            # process.
            # Technical note: if there is no attribute, a variant is still created because
            # 'not any([])' and 'set([]) not in set([])' are True.
            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.template.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_combinations = itertools.product(*[
                    ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                ])
                # For each possible variant, create if it doesn't exist yet.
                for combination_tuple in all_combinations:
                    combination = self.env['product.template.attribute.value'].concat(*combination_tuple)
                    if combination in existing_variants:
                        current_variants_to_activate += existing_variants[combination]
                    else:
                        current_variants_to_create.append({
                            'product_tmpl_id': tmpl_id.id,
                            'product_template_attribute_value_ids': [(6, 0, combination.ids)],
                            'active': tmpl_id.active,
                        })
                        if len(current_variants_to_create) > 1000:
                            raise UserError(_(
                                'The number of variants to generate is too high. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))
                variants_to_create += current_variants_to_create
                variants_to_activate += current_variants_to_activate

            else:
                for variant in existing_variants.values():
                    is_combination_possible = self._is_combination_possible_by_config(
                        combination=variant.product_template_attribute_value_ids,
                        ignore_no_variant=True,
                    )
                    if is_combination_possible:
                        current_variants_to_activate += variant
                variants_to_activate += current_variants_to_activate

            variants_to_unlink += all_variants - current_variants_to_activate

        if variants_to_activate:
            variants_to_activate.write({'active': True})
        if variants_to_create:
            res_products = Product.create(variants_to_create)
            for Prod in res_products:
                if Prod.name:
                    product_sku_obj = self.env['product.auto.sku']
                    sku_info_id = product_sku_obj.search([])
                    seq_id = self.env['ir.sequence'].search([('name', 'ilike', 'Product Sequence')])

                    if sku_info_id.enable == True:
                        if sku_info_id.sequence == 'one':
                            seq_id.write({'padding': 2})
                        if sku_info_id.sequence == 'two':
                            seq_id.write({'padding': 3})
                        if sku_info_id.sequence == 'three':
                            seq_id.write({'padding': 4})
                        if sku_info_id.sequence == 'four':
                            seq_id.write({'padding': 5})
                        if sku_info_id.sequence == 'five':
                            seq_id.write({'padding': 6})
                        if sku_info_id.sequence == 'six':
                            seq_id.write({'padding': 7})
                        if sku_info_id.sequence == 'seven':
                            seq_id.write({'padding': 8})
                        if sku_info_id.sequence == 'eight':
                            seq_id.write({'padding': 9})
                        if sku_info_id.sequence == 'nine':
                            seq_id.write({'padding': 10})
                        if sku_info_id.sequence == 'ten':
                            seq_id.write({'padding': 11})

                        supplier_name = ''
                        sku_hyphens = ''
                        sort_pro_name = ''
                        value = ''
                        sku_n = ''
                        sku_m = ''
                        sku = ''

                        if sku_info_id.sku_by_supplier == 'first_two':
                            for supplier in Prod.seller_ids:
                                part_name = supplier[0].partner_id
                                supplier_name = part_name.name[:2].upper()
                        if sku_info_id.sku_by_supplier == 'define_supp':
                            for supplier in Prod.seller_ids:
                                part_name = supplier[0].partner_id
                                supplier_name = part_name.short_name.upper()
                        if sku_info_id.sku_by_product == 'first_four':
                            product_name = Prod.categ_id.name
                            sort_pro_name = product_name[:4].upper()

                        if sku_info_id.sku_by_product == 'short_code':
                            product_name = Prod.categ_id.short_code if Prod.categ_id.short_code else ''
                            sort_pro_name = product_name

                        # if sku_info_id.sku_by_attribute == 'three_latter':
                        #     if vals.get('attribute_value_ids', []):
                        #         for att_value in res.attribute_value_ids:
                        #             if sku_info_id.hyphens == True:
                        #                 value = value + str(att_value.name[:3] + '.').upper()
                        #             else:
                        #                 value = value + str(att_value.name[:3]).upper()
                        # if sku_info_id.sku_by_attribute == 'one_latter':
                        #     for att_value in res.attribute_value_ids:
                        #         if sku_info_id.hyphens == True:
                        #             value = value + str(att_value.name[:1] + '.').upper()
                        #         else:
                        #             value = value + str(att_value.name[:1]).upper()

                        pro_seq = self.env['ir.sequence'].next_by_code('product.sequence')
                        if sku_info_id.hyphens == True:
                            sku_hyphens = '.'
                            if str(supplier_name) != '':
                                sku_n = str(supplier_name) + str(sku_hyphens)
                            if str(sort_pro_name) != '':
                                sku_m = sku_n + str(sort_pro_name) + str(sku_hyphens)
                            if str(value) != '':
                                sku = sku_m + str(value) + str(pro_seq)
                            else:
                                sku = sku_m + str(pro_seq)

                            Prod.default_code = sku
                            Prod.pro_sequence = pro_seq

        if variants_to_unlink:
            variants_to_unlink._unlink_or_archive()

        # prefetched o2m have to be reloaded (because of active_test)
        # (eg. product.template: product_variant_ids)
        # We can't rely on existing invalidate_cache because of the savepoint
        # in _unlink_or_archive.
        self.env.flush_all()
        self.env.invalidate_all()
        # raise UserWarning('TEST')
        return True


    def _set_default_code(self):
        for template in self:
            if not template.default_code:
                if len(template.product_variant_ids) == 1:
                    if self.name:
                        product_sku_obj = self.env['product.auto.sku']
                        sku_info_id = product_sku_obj.search([])
                        seq_id = self.env['ir.sequence'].search([('name', 'ilike', 'Product Sequence')])
                        if sku_info_id.enable == True:
                            if sku_info_id.sequence == 'one':
                                seq_id.write({'padding': 2})
                            if sku_info_id.sequence == 'two':
                                seq_id.write({'padding': 3})
                            if sku_info_id.sequence == 'three':
                                seq_id.write({'padding': 4})
                            if sku_info_id.sequence == 'four':
                                seq_id.write({'padding': 5})
                            if sku_info_id.sequence == 'five':
                                seq_id.write({'padding': 6})
                            if sku_info_id.sequence == 'six':
                                seq_id.write({'padding': 7})
                            if sku_info_id.sequence == 'seven':
                                seq_id.write({'padding': 8})
                            if sku_info_id.sequence == 'eight':
                                seq_id.write({'padding': 9})
                            if sku_info_id.sequence == 'nine':
                                seq_id.write({'padding': 10})
                            if sku_info_id.sequence == 'ten':
                                seq_id.write({'padding': 11})

                            supplier_name = ''
                            sku_hyphens = ''
                            sort_pro_name = ''
                            value = ''
                            sku_n = ''
                            sku_m = ''
                            sku = ''
                            if sku_info_id.sku_by_supplier == 'first_two':
                                for supplier in self.seller_ids:
                                    part_name = supplier[0].partner_id
                                    supplier_name = part_name.name[:2].upper()
                            if sku_info_id.sku_by_supplier == 'define_supp':
                                for supplier in self.seller_ids:
                                    part_name = supplier[0].partner_id
                                    supplier_name = part_name.short_name.upper()
                            if sku_info_id.sku_by_product == 'first_four':
                                product_name = self.categ_id.name
                                sort_pro_name = product_name[:4].upper()

                            if sku_info_id.sku_by_product == 'short_code':
                                product_name = self.categ_id.short_code if self.categ_id.short_code else ''
                                sort_pro_name = product_name

                            # if sku_info_id.sku_by_attribute == 'three_latter':
                            #     if vals.get('attribute_value_ids', []):
                            #         for att_value in res.attribute_value_ids:
                            #             if sku_info_id.hyphens == True:
                            #                 value = value + str(att_value.name[:3] + '.').upper()
                            #             else:
                            #                 value = value + str(att_value.name[:3]).upper()
                            # if sku_info_id.sku_by_attribute == 'one_latter':
                            #     for att_value in res.attribute_value_ids:
                            #         if sku_info_id.hyphens == True:
                            #             value = value + str(att_value.name[:1] + '.').upper()
                            #         else:
                            #             value = value + str(att_value.name[:1]).upper()


                            pro_seq = self.product_variant_ids.pro_sequence

                            if sku_info_id.hyphens == True:
                                sku_hyphens = '.'
                                if str(supplier_name) != '':
                                    sku_n = str(supplier_name) + str(sku_hyphens)
                                if str(sort_pro_name) != '':
                                    sku_m = sku_n + str(sort_pro_name) + str(sku_hyphens)
                                if str(value) != '':
                                    sku = sku_m + str(value) + str(pro_seq)
                                else:
                                    sku = sku_m + str(pro_seq)
                            else:
                                sku = str(supplier_name) + str(sort_pro_name) + str(value) + str(pro_seq)

                            self.pro_sequence = pro_seq

                            template.default_code = sku
                            template.product_variant_ids.default_code = template.default_code
