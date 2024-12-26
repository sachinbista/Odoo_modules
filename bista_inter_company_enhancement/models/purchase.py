# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def create(self, vals):
        """
            Added serial from SO Line to PO Line ( Xidax SO Line --> Xidax PO Line)

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        po = False
        so_id = False
        res = super(PurchaseOrderLine, self).create(vals)
        for rec in res:
            rec.sudo().update({'bs_lot_ids': [(6, 0, rec.sale_line_id.bs_lot_ids.ids)]})
            so_id = rec.sale_line_id.order_id.id
            po = rec.order_id
        if po:
            po.with_context({'allow_edit': True}).sudo().update({'bs_inter_so_id': so_id})
        if po and po.company_id.bs_auto_validate_PO and po.bs_inter_so_id:
            po.sudo().with_context({'allow_edit': True}).button_confirm()
        return res

    bs_lot_ids = fields.Many2many(
        "stock.lot",
        string="Serial",
        copy=False, readonly=False
    )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    bs_inter_so_id = fields.Many2one('sale.order', string='Xidax SO Ref', store=True, copy=False)

    def button_confirm(self):
        """
            Inherit for passing additional context to manual PO confirm

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        additional_context = {'allow_edit': True}
        # Call the super method with the additional context
        result = super(PurchaseOrder, self.with_context(additional_context)).button_confirm()
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
                raise UserError("You cannot change anything from PO Line. Hints : Cancel SO --> Reset to draft ")

    def write(self, vals):
        """
            INHERIT FOR RESTRICT VALUES FOR INTER COMPANY

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """

        updated_data = dict(self._context)
        if (self.bs_inter_so_id and not updated_data.get('allow_edit') == True and vals.get('state') != 'cancel') or (
                self.bs_inter_so_id and 'allow_edit' not in updated_data and vals.get('state') != 'cancel'):
            raise UserError("You cannot change anything from PO. Hints : Cancel SO --> Reset to draft ")
        return super(PurchaseOrder, self).write(vals)

    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        """
            Generate the Sales Order Line values from the PO line along with serial
            ( Xidax PO Line --> PCL SO Line )

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        res = super(PurchaseOrder, self)._prepare_sale_order_line_data(line, company)
        lot_lst = []
        for lot in line.bs_lot_ids:
            if lot:
                lot_ids = self.env['stock.lot'].search(
                    [('name', '=', lot.name), ('product_id', '=', line.product_id.id)],
                    limit=1).id
                lot_lst.append(lot_ids)
        # res.update({'bs_lot_ids': [(6, 0, lot_lst)], 'bs_po_line_id': line.id})
        return res

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        """
        This function updates the partner_shipping_id on the other company where SO,
        is created on the confirmation of PO.
        """
        res = super(PurchaseOrder, self)._prepare_sale_order_data(name, partner, company, direct_delivery_address)
        order_lines = self.bs_inter_so_id.order_line
        order_line_data = []

        # for order_line in order_lines:
        #     if order_line.product_id.detailed_type == 'service':
        #         order_line_data.append((0, 0, {
        #             'name': order_line.name,
        #             'product_uom_qty': order_line.product_uom_qty,
        #             'product_id': order_line.product_id.id,
        #             'product_uom': order_line.product_uom.id,
        #             'price_unit': order_line.price_unit,
        #             # Add other fields as needed
        #         }))

        sale_order_ids = self._get_sale_orders()
        if sale_order_ids:
            sale_order_id = sale_order_ids[-1]
            res.update({
                'allow_do_dropship': True,
                'partner_shipping_id': sale_order_id.partner_shipping_id.id,
                'payment_term_id': sale_order_id.payment_term_id.id,
                'is_free_shipping': True if sale_order_ids.company_id.id == 4 else False,
                'sale_channel': sale_order_id.sale_channel.id,
                'order_line': order_line_data,
                'ship_via': sale_order_id.ship_via,
                'bs_inter_so_id': sale_order_id.id,
                'picking_policy': 'one',
                'customer_po': sale_order_id.shopify_order_name
            })
        return res
