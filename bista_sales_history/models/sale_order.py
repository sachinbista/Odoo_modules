# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_sales_history(self):
        context = self._context.copy()
        ref = self.partner_id.ref
        if not ref:
            raise UserError(_('Please Enter Customer Reference in Customer Record'))
        cr = self._cr
        cr.execute("select max(id) from sale_history_line where contact_reference is not null and contact_reference ilike '%s' group by product_name" % (ref))
        sale_history_line_id = list(filter(None, map(lambda x: x[-1], cr.fetchall())))
        if sale_history_line_id:
            context.update({'contact_reference_id': sale_history_line_id[0]})
        else:
            raise ValidationError(_('No Sales History Data Found.'))
        return {
                    'type': 'ir.actions.act_window',
                    'name': 'Sales History',
                    'view_mode': 'form',
                    'res_model': 'sales.inquiry.wizard',
                    'target': 'new',
                    'context': context
                }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def get_sales_history(self):
        context = self._context.copy()
        ref = self.order_id.partner_id.ref
        if not ref:
            raise UserError(_('Please Enter Customer Reference in Customer Record'))
        cr = self._cr
        cr.execute("select max(id) from sale_history_line where contact_reference is not null and contact_reference ilike '%s' group by product_name" % (ref))
        sale_history_line_id_customer = list(filter(None, map(lambda x: x[0], cr.fetchall())))
        if sale_history_line_id_customer:
            context.update({'contact_reference_id': sale_history_line_id_customer[-1]})
        product_id_brw = self.product_id
        product_name = product_id_brw.name
        product_id = product_id_brw.id
        inventory_id = product_id_brw.inventory_vendor_id
        cr.execute("select max(id) from sale_history_line where (product_name is not null and product_name ilike '%s' and inventory_short_vendor_name ='%s') or (product_id=%s) group by product_name" % (product_name, inventory_id.short_name if inventory_id and inventory_id.short_name else '', product_id))
        sale_history_line_id_product = list(filter(None, map(lambda x: x[0], cr.fetchall())))
        if sale_history_line_id_product:
            context.update({'product_id': sale_history_line_id_product[-1]})
        if not sale_history_line_id_customer and sale_history_line_id_product:
            raise ValidationError(_('No Sales History Data Found.'))
        return {
                    'type': 'ir.actions.act_window',
                    'name': 'Sales History',
                    'view_mode': 'form',
                    'res_model': 'sales.inquiry.wizard',
                    'target': 'new',
                    'context': context
                }                



