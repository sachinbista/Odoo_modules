# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api
from odoo.exceptions import UserError
from lxml import etree


class SaleOrder(models.Model):
    _inherit = "sale.order"

    bs_inter_so_id = fields.Many2one('sale.order', string='Xidax SO Ref', copy=False)

    def action_confirm(self):
        """
            Inherit for passing additional context to manual SO confirm

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        additional_context = {'allow_edit': True}
        # Call the super method with the additional context
        result = super(SaleOrder, self.with_context(additional_context)).action_confirm()
        # You can now use the result or perform any additional actions
        return result

    @api.onchange('order_line')
    def _onchange_order_line(self):
        """
            Added restriction on order line for inter-company

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        if self.order_line:
            updated_data = dict(self._context)
            if (self.bs_inter_so_id and not updated_data.get('allow_edit') == True and self.state != 'cancel') or (
                    self.bs_inter_so_id and 'allow_edit' not in updated_data and self.state != 'cancel'):
                raise UserError("You cannot change anything from SO Line. Hints : Cancel SO --> Reset to draft ")

    def write(self, vals):
        """
            Inherit for restrict values for inter-company

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        context = self._context.copy()
        context.update({'allow_edit': True})
        if (self.bs_inter_so_id and not context.get('allow_edit') == True and vals.get('state') != 'cancel') or (
                self.bs_inter_so_id and 'allow_edit' not in context and vals.get('state') != 'cancel'):
            raise UserError("You cannot change anything from SO. Hints : Cancel SO --> Reset to draft ")
        return super(SaleOrder, self).write(vals)

    def _action_confirm(self):
        """
            This function is added to Check Availability of Delivery Order.

            :return:
            @author: Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """
        res = super(SaleOrder, self)._action_confirm()
        for order in self:
            picking_ids = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            if order.auto_generated and picking_ids:
                for picking_id in picking_ids:
                    picking_id.action_assign()

        return res

    def action_cancel(self):
        """
            This function is added to allow user to Cancel SO based on Delivered/Invoiced Quantities of Products is SO.

            :return:
            @author: Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """
        for order in self:
            so_lines = order.order_line
            for line in so_lines:
                if line.qty_invoiced > 0 or line.product_template_id.detailed_type in ('consu', 'product') and (
                        line.qty_delivered > 0):
                    raise UserError("There is an Invoice or Delivery associated with the Sale Order. "
                                    "Before cancelling the Sale Order, Kindly Return the Delivery if it's delivered "
                                    "to the customer and Refund/Cancel an Invoice if it's Paid/Posted.")

        return super(SaleOrder, self).action_cancel()

    def bs_start_new(self):
        """
            This function is allow order cancel and reset in draft.

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        for order in self:
            order.with_context({'disable_cancel_warning': True, 'allow_edit': True}).action_cancel()
            order.with_context({'allow_edit': True}).action_draft()
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Now you can reuse the record',
                'type': 'rainbow_man',
            }
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bs_lot_ids = fields.Many2many('purchase.order.line', string="Bs lot Id")

    @api.model
    def create(self, vals):
        """
            Inherit for updating SO ref
            Xidax PO ---> PCL SO

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        res = super(SaleOrderLine, self).create(vals)
        # if res and res.bs_po_line_id:
        #     res.order_id.with_context({'allow_edit': True}).update({'bs_inter_so_id':res.bs_po_line_id.order_id.bs_inter_so_id.id})
        return res
