# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class PurchaseOrderManualReceiptLine(models.TransientModel):
    _name = 'purchase.order.manual.receipt.line'

    manual_receipt_id = fields.Many2one('purchase.order.manual.receipt.wizard')
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", related='manual_receipt_id.purchase_order_id')
    uom_category_id = fields.Many2one('uom.category', string="Category", related='product_id.uom_id.category_id')
    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase Line")
    product_id = fields.Many2one('product.product', string="Product", related='purchase_line_id.product_id')
    product_uom_qty = fields.Float('Quantity')
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    currency_id = fields.Many2one('res.currency', string="Currency", related='purchase_line_id.currency_id')
    unit_price = fields.Monetary(string='Unit Price')

    
    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        self.ensure_one()
        product = self.product_id.with_context(lang=self.purchase_order_id.dest_address_id.lang or self.env.user.lang)
        date_planned = self.manual_receipt_id.scheduled_date
        return {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.product_id.display_name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': self.purchase_order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': self.purchase_order_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.purchase_order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.purchase_line_id.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.purchase_line_id.id,
            'company_id': self.purchase_order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.manual_receipt_id.picking_type_id.id,
            'group_id': self.purchase_order_id.group_id.id,
            'origin': self.purchase_order_id.name,
            'description_picking': product.description_pickingin or self.purchase_line_id.name,
            'propagate_cancel': self.purchase_line_id.propagate_cancel,
            'warehouse_id': self.manual_receipt_id.picking_type_id.warehouse_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
            'product_packaging_id': self.purchase_line_id.product_packaging_id.id,
            'sequence': self.purchase_line_id.sequence,
        }

    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res

        price_unit = self.purchase_line_id._get_stock_move_price_unit()
        product_uom_qty = self.product_uom_qty

        res.append(self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, self.uom_id))
        return res

    def _create_stock_moves(self, picking):
        values = []
        for line in self:
            for val in line._prepare_stock_moves(picking):
                values.append(val)
            line.purchase_line_id.manually_received_qty_uom += line.product_uom_qty

        return self.env['stock.move'].sudo().create(values)