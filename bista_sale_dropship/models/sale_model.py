# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError

from odoo import api, models, fields, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    purchase_count = fields.Integer(
        string='# of Purchases', compute='_compute_purchase', readonly=True)

    def _compute_purchase(self):
        purchase_order_obj = self.env['purchase.order']
        if self:
            for rec in self:
                rec.purchase_count = 0
                po_count = purchase_order_obj.search_count(
                    [('sh_sale_order_id', '=', rec.id)])
                rec.purchase_count = po_count

    def action_view_purchases(self):
        purchase_order_obj = self.env['purchase.order']
        if self and self.id:
            if self.purchase_count == 1:
                po_search = purchase_order_obj.search(
                    [('sh_sale_order_id', '=', self.id)], limit=1)
                if po_search:
                    return {
                        "type": "ir.actions.act_window",
                        "res_model": "purchase.order",
                        "views": [[False, "form"]],
                        "res_id": po_search.id,
                        "target": "self",
                    }
            if self.purchase_count > 1:
                po_search = purchase_order_obj.search(
                    [('sh_sale_order_id', '=', self.id)])
                if po_search:
                    action = self.sudo().env.ref('purchase.purchase_rfq').read()[0]
                    action['domain'] = [('id', 'in', po_search.ids)]
                    action['target'] = 'self'
                    return action

    def create_dropship(self):
        """
            this method fire the action and open create dropship purchase order wizard
        """
        view = self.sudo().env.ref('bista_sale_dropship.bista_sale_dropship_purchase_order_wizard')
        return {
            'name': 'Create Dropship Order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'partner_shipping_id': self.partner_shipping_id.id if self.partner_shipping_id else False
            },
        }

    def action_check(self):
        if self.order_line:
            for line in self.order_line.filtered(
                    lambda line: line.product_uom_qty != line.qty_delivered and not line.product_id.type == 'service'):
                if not line.check_existing_stock_moves():
                    line.tick = True

    def action_uncheck(self):
        if self.order_line:
            for line in self.order_line:
                line.tick = False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tick = fields.Boolean(copy=False,help="Select Product for Dropship Order")
    is_dropship = fields.Boolean(string="Is Dropship", copy=False)

    @api.onchange('tick')
    def onchange_tick(self):
        if self.qty_delivered == self.product_uom_qty:
            raise ValidationError(_("Cannot select this item as it is already delivered."))
        if self.check_existing_stock_moves():
            raise ValidationError(_("Delivery already exist for this product."))

    def check_existing_stock_moves(self):
        for each_rec in self:
            outgoing_move_ids, incoming_move_ids = each_rec._get_outgoing_incoming_moves()
            move_ids = outgoing_move_ids.filtered(lambda x: x.state == 'assigned')
            if move_ids and "DS" in move_ids.reference:
                return True
            else:
                return False

    def _prepare_invoice_line(self, **optional_values):
        """
            Made is_dropship boolean true if sale order line is dropship
        """
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        values.update({'is_dropship': self.is_dropship})
        return values
