# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_service_lines = fields.One2many(
        'sale.order.line',
        compute='_compute_website_service_line',
        string='Order Lines service items',
    )

    website_other_lines = fields.One2many(
        'sale.order.line',
        compute='_compute_website_other_line',
        string='Order Lines service items',
    )

    @api.depends('user_id', 'company_id','partner_id')
    def _compute_warehouse_id(self):
        for order in self:
            if order.partner_id and order.partner_id.warehouse_id:
                default_warehouse_id = order.partner_id.warehouse_id.id
            else:
                default_warehouse_id = self.env['ir.default'].with_company(
                    order.company_id.id)._get_model_defaults('sale.order').get('warehouse_id')
            if order.state in ['draft', 'sent'] or not order.ids:
                # Should expect empty
                if default_warehouse_id is not None:
                    order.warehouse_id = default_warehouse_id
                else:
                    order.warehouse_id = order.user_id.with_company(order.company_id.id)._get_default_warehouse_id()

    def _cart_find_product_line(
            self, product_id=None, line_id=None,
            linked_line_id=False, optional_product_ids=None, **kwargs):
        lines = super()._cart_find_product_line(product_id, line_id, **kwargs)
        if not line_id:
            service_id = kwargs.get("service_id") or 0
            order_lines = lines.filtered(lambda l: l.service_id.id == int(service_id))
            if order_lines:
                lines = order_lines[0]
            else:
                lines = self.env['sale.order.line']
        return lines

    @api.depends('order_line')
    def _compute_website_service_line(self):
        for order in self:
            order.website_service_lines = order.order_line.filtered(lambda l: l._is_service_line())

    @api.depends('order_line')
    def _compute_website_other_line(self):
        for order in self:
            order.website_other_lines = order.order_line.filtered(
                lambda l: not l._is_service_line() and not l.service_id)

    @api.model_create_multi
    def create(self, vals_list):

        # asd = []
        # dict1 = {}
        # dict2 = {}
        res = super(SaleOrder, self).create(vals_list)
        for rec in self:
            rec.check_section_line_exist()
        # for order in res:
        #     for line in order.order_line:
        #         if line.product_id.detailed_type == 'service' and len(line.product_id.allowed_products.ids) > 0:
        #             if res.partner_id.id not in line.product_id.allowed_customers.ids:
        #                 raise UserError("This service product cannot be added for this customer.")
        #         if line.display_type == 'line_section':
        #             asd = []
        #             dict1.update({line: asd})
        #         if line.product_id:
        #             asd.append(line.product_id)
        #     # for checking unique service
        #     check_one_service = []
        #     for line in dict1:
        #         if line.product_id.detailed_type == 'service':
        #             if order.partner_id.id not in line.product_id.allowed_customers.ids:
        #                 raise UserError("This service product cannot be added for this customer.")
        #             check_one_service.append(line.product_id)
        #         if len(check_one_service) > 1:
        #             raise UserError(
        #                 "This service product cannot be added because this sections already have the product as a services."
        #             )
        # if not dict1:
        #     # for line in rec.order_line:
        #     # if line.display_type != 'line_section':
        #     service_product_lst = res.order_line.filtered(
        #         lambda line: line.product_id and line.product_id.detailed_type == 'service' and len(
        #             line.product_id.allowed_products) > 0)
        #     if len(service_product_lst) > 1:
        #         raise UserError("Can not add more than one service product.")
        #     elif len(service_product_lst) == 1:
        #         service_product_id = service_product_lst.product_id
        #         service_product_allowed_product_lst = service_product_id.allowed_products.ids
        #         normal_product_lst = res.order_line.filtered(
        #             lambda line: line.product_id and line.product_id.detailed_type != 'service').mapped(
        #             'product_id').ids
        #         matching_products = res.check_all_products(service_product_allowed_product_lst, normal_product_lst)
        #
        #         if not matching_products:
        #             raise UserError(
        #                 "This product is not allowed to selected Service products."
        #             )
        #         if res.partner_id.id not in service_product_id.allowed_customers.ids:
        #             raise UserError(
        #                 "This service product cannot be added for this customer.")
        #
        #     # check the allowed products in service sections
        #     for line in dict1:
        #         asd = []
        #         for product_id in dict1[line]:
        #             if product_id.detailed_type == 'service':
        #                 dict2.update({product_id: asd})
        #             else:
        #                 asd.append(product_id.id)
        #     for i in dict2:
        #         for lin in dict2[i]:
        #             if lin not in i.allowed_products.ids and not any(line.is_delivery for line in order.order_line):
        #                 raise UserError(
        #                     "Sections already have different services as a product."
        #                 )
        return res

    def write(self, values):
        """
        create section if not exist so create a new section.
        :param values:
        :return:
        """
        # self.section_line_create(values)
        res = super(SaleOrder, self).write(values)
        for rec in self:
            rec.check_section_line_exist()
        return res

    def check_all_products(self, service_product_allowed_product_lst, normal_product_lst):
        for product in normal_product_lst:
            if product not in service_product_allowed_product_lst:
                return False
        return True

    def check_section_line_exist(self):
        for order in self:
            section_product_map = self.sectionwise_product_orderline()
            for section, lines in section_product_map.items():
                service_lines = [line for line in lines if line.product_id.detailed_type == 'service']
                product_lines = [line for line in lines if line.product_id.detailed_type != 'service']
                if len(service_lines) > 1:
                    raise ValidationError("Can not add more than one service product.")
                for line in service_lines:
                    if self.partner_id.id not in line.product_id.allowed_customers.ids and not any(
                            l.is_delivery for l in order.order_line):
                        raise ValidationError("This service product cannot be added for this customer.")
                if service_lines:
                    allowed_products = service_lines[0].product_id.allowed_products
                    for line in product_lines:
                        if line.product_id not in allowed_products:
                            raise ValidationError("This product is not allowed to selected Service products.")

    def sectionwise_product_orderline(self):
        section_product_map = {}
        current_section = None
        for line in self.order_line.sorted(lambda a: a.sequence):
            if line.display_type == 'line_section':
                current_section = line
                section_product_map[current_section] = []
            elif current_section:
                section_product_map[current_section].append(line)
            else:
                section_product_map.setdefault(None, []).append(line)
        return section_product_map

    def _prepare_order_line_values(
            self, product_id, quantity, linked_line_id=False,
            no_variant_attribute_values=None, product_custom_attribute_values=None,
            **kwargs
    ):
        values = super()._prepare_order_line_values(product_id, quantity, linked_line_id,
                                                    no_variant_attribute_values,
                                                    product_custom_attribute_values, **kwargs)
        if kwargs.get('sequence'):
            values['sequence'] = kwargs.get('sequence')
        if kwargs.get("service_id"):
            values['service_id'] = kwargs.get('service_id')
        return values

    def _prepare_delivery_line_vals(self, carrier, price_unit):
        res = super()._prepare_delivery_line_vals(carrier, price_unit)
        existing_delivery_section = self.env['sale.order.line'].sudo().search([('display_type', '=', 'line_section')],
                                                                              limit=1)
        delivery_section = self.env['sale.order.line'].sudo().search([
            ('order_id', '=', self.id),
            ('display_type', '=', 'line_section'),
            ('name', '=', 'Delivery')
        ], limit=1)
        if existing_delivery_section and not delivery_section:
            # self.delivery_section = True
            self.env['sale.order.line'].create({
                'order_id': self.id,
                'name': 'Delivery',
                'display_type': 'line_section',
                'delivery_section': True,
                'sequence': max(self.order_line.mapped('sequence')) + 1,
            })
        return res
