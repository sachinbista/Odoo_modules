##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from odoo.tools import format_datetime, formatLang


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    base = fields.Selection(selection_add=[('msrp', 'MSRP')],
                            ondelete={'msrp': 'cascade'}, default='list_price', )


#
#     categ_id = fields.Many2many(
#         comodel_name='product.category',
#         string="Product Category",
#         ondelete='cascade',
#         help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
#
#     @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
#         'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
#     def _compute_name_and_price(self):
#         for item in self:
#             categ_name = []
#             for categ in item.categ_id:
#                 categ_name.append(categ.display_name)
#             if item.categ_id and item.applied_on == '2_product_category':
#                 # item.name = _("Category: %s") % (categ.display_name)
#                 item.name = _("Category: %s") % (', '.join(categ_name))
#             elif item.product_tmpl_id and item.applied_on == '1_product':
#                 item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
#             elif item.product_id and item.applied_on == '0_product_variant':
#                 item.name = _("Variant: %s") % (item.product_id.display_name)
#             else:
#                 item.name = _("All Products")
#
#             if item.compute_price == 'fixed':
#                 item.price = formatLang(
#                     item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
#             elif item.compute_price == 'percentage':
#                 item.price = _("%s %% discount", item.percent_price)
#             else:
#                 item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)
#
#     def _is_applicable_for(self, product, qty_in_product_uom):
#         """Check whether the current rule is valid for the given product & qty.
#
#         Note: self.ensure_one()
#
#         :param product: product record (product.product/product.template)
#         :param float qty_in_product_uom: quantity, expressed in product UoM
#         :returns: Whether rules is valid or not
#         :rtype: bool
#         """
#         self.ensure_one()
#         product.ensure_one()
#         res = True
#
#         is_product_template = product._name == 'product.template'
#         if self.min_quantity and qty_in_product_uom < self.min_quantity:
#             res = False
#         elif self.applied_on == "2_product_category":
#             for rec in self.categ_id:
#                 if (
#                     product.categ_id != rec
#
#                 ):
#                     res = False
#         else:
#             # Applied on a specific product template/variant
#             if is_product_template:
#                 if self.applied_on == "1_product" and product.id != self.product_tmpl_id.id:
#                     res = False
#                 elif self.applied_on == "0_product_variant" and not (
#                     product.product_variant_count == 1
#                     and product.product_variant_id.id == self.product_id.id
#                 ):
#                     # product self acceptable on template if has only one variant
#                     res = False
#             else:
#                 if self.applied_on == "1_product" and product.product_tmpl_id.id != self.product_tmpl_id.id:
#                     res = False
#                 elif self.applied_on == "0_product_variant" and product.id != self.product_id.id:
#                     res = False
#
#         return res


# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'
#
#     pricelist_item_id = fields.Many2many(
#         comodel_name='product.pricelist.item',
#         compute='_compute_pricelist_item_id')


# -*- coding: utf-8 -*-


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"


    categ_id = fields.Many2many('product.category', string="Category")

    def _get_applicable_rules_domain(self, products, date, **kwargs):
        if products._name == 'product.template':
            templates_domain = ('product_tmpl_id', 'in', products.ids)
            products_domain = ('product_id.product_tmpl_id', 'in', products.ids)
        else:
            templates_domain = ('product_tmpl_id', 'in', products.product_tmpl_id.ids)
            products_domain = ('product_id', 'in', products.ids)
        return [
            ('pricelist_id', '=', self.id),
            '|', ('categ_id', 'in', []), ('categ_id', 'parent_of', products.categ_id.ids),
            '|', ('product_tmpl_id', '=', False), templates_domain,
            '|', ('product_id', '=', False), products_domain,
            '|', ('date_start', '=', False), ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
        ]

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _compute_name_and_price(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s") % (item.categ_id[0].display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = _("Variant: %s") % (item.product_id.display_name)
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                item.price = formatLang(
                    item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount", item.percent_price)
            else:
                item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount,
                               price=item.price_surcharge)

    @api.constrains('product_id', 'product_tmpl_id', 'categ_id')
    def _check_product_consistency(self):
        for item in self:
            if item.applied_on == "2_product_category" and not item.categ_id:
                raise ValidationError(_("Please specify the category for which this rule should be applied"))
            elif item.applied_on == "1_product" and not item.product_tmpl_id:
                raise ValidationError(_("Please specify the product for which this rule should be applied"))
            elif item.applied_on == "0_product_variant" and not item.product_id:
                raise ValidationError(_("Please specify the product variant for which this rule should be applied"))

    @api.onchange('product_id', 'product_tmpl_id', 'categ_id')
    def _onchange_rule_content(self):
        if not self.user_has_groups('product.group_sale_pricelist') and not self.env.context.get('default_applied_on',
                                                                                                 False):
            # If advanced pricelists are disabled (applied_on field is not visible)
            # AND we aren't coming from a specific product template/variant.
            variants_rules = self.filtered('product_id')
            template_rules = (self - variants_rules).filtered('product_tmpl_id')
            variants_rules.update({'applied_on': '0_product_variant'})
            template_rules.update({'applied_on': '1_product'})
            (self - variants_rules - template_rules).update({'applied_on': '3_global'})

    def _is_applicable_for(self, product, qty_in_product_uom):
        """Check whether the current rule is valid for the given product & qty.

        Note: self.ensure_one()

        :param product: product record (product.product/product.template)
        :param float qty_in_product_uom: quantity, expressed in product UoM
        :returns: Whether rules is valid or not
        :rtype: bool
        """
        self.ensure_one()
        product.ensure_one()
        res = True

        is_product_template = product._name == 'product.template'
        if self.min_quantity and qty_in_product_uom < self.min_quantity:
            res = False

        elif self.applied_on == "2_product_category":
            if (
                    product.categ_id.id not in self.categ_id.ids
                    and not product.categ_id.parent_path.startswith(self.categ_id.parent_path)
            ):
                res = False
        else:
            # Applied on a specific product template/variant
            if is_product_template:
                if self.applied_on == "1_product" and product.id != self.product_tmpl_id.id:
                    res = False
                elif self.applied_on == "0_product_variant" and not (
                        product.product_variant_count == 1
                        and product.product_variant_id.id == self.product_id.id
                ):
                    # product self acceptable on template if has only one variant
                    res = False
            else:
                if self.applied_on == "1_product" and product.product_tmpl_id.id != self.product_tmpl_id.id:
                    res = False
                elif self.applied_on == "0_product_variant" and product.id != self.product_id.id:
                    res = False

        return res