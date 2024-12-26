# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_special = fields.Boolean(string="Is Special", copy=False)

    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        if self.is_special:
            values.update({'is_special': self.is_special})
        return values

    def write(self, values):
        if 'is_special' in values:
            orders = self.mapped('order_id')
            for order in orders:
                order_lines = self.filtered(lambda x: x.order_id == order)
                msg = "<b>" + _("Is Special has been updated.") + "</b><ul>"
                for line in order_lines:
                    move_ids = line.move_ids.filtered(lambda l: l.sale_line_id.id == line.id)
                    if move_ids:
                        move_ids.write({'is_special': values['is_special']})
                    msg += "<li> %s: <br/>" % line.product_id.display_name
                    msg += _(
                        "Is Special: %(old_value)s --> %(new_value)s",
                        old_value=line.is_special,
                        new_value=values["is_special"]
                    ) + "<br/>"
                msg += "</ul>"
                order.message_post(body=msg)
        return super(SaleOrderLine, self).write(values)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    def _prepare_order_line_values(
            self, product_id, quantity, linked_line_id=False,
            no_variant_attribute_values=None, product_custom_attribute_values=None,
            **kwargs
    ):
        lines = super()._prepare_order_line_values(product_id=product_id, quantity=quantity, linked_line_id=linked_line_id,
            no_variant_attribute_values=no_variant_attribute_values, product_custom_attribute_values=product_custom_attribute_values,
            **kwargs)
        if product_custom_attribute_values:
            lines.update({'is_special':True})
        return lines