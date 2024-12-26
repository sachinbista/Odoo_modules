# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleSplitWizard(models.TransientModel):
    _name = 'sale.split.wizard'
    _description = "Sale Split Wizard"

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    order_line = fields.One2many(
        'sale.split.line.wizard', 'wizard_id', string='Order Lines')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    @api.model
    def default_get(self, fields):
        res = super(SaleSplitWizard, self).default_get(fields)
        active_so_id = self.env.context.get("active_id")
        sale_order_obj = self.env['sale.order']
        if active_so_id:
            sale_order_search = sale_order_obj.browse(active_so_id)
            if sale_order_search and sale_order_search.order_line:
                line_vals = []
                for order_line in sale_order_search.order_line:
                    lines = self.create_order_line_list(order_line)
                    if lines:
                        line_vals.append(lines)
                res.update({
                    'partner_id': sale_order_search.partner_id.id,
                    'sale_order_id': sale_order_search.id,
                    'order_line': line_vals})
        return res

    def create_order_line_list(self, order_line):
        """
        Function to create wizard order lines from current sale order.
        :param order_line: sale order line.
        :return: lines to be inserted into wizard order line.
        """
        qty = order_line.product_uom_qty - order_line.qty_delivered
        if qty:
            return fields.Command.create({'name': order_line.name,
                                          'product_id': order_line.product_id.id,
                                          'product_qty': qty,
                                          'price_unit': order_line.price_unit,
                                          'product_uom': order_line.product_uom.id,
                                          'so_line_id': order_line.id,
                                          # 'price_subtotal': order_line.price_subtotal
                                          })
        else:
            return False

    def split_and_hold(self):
        if sum(self.sale_order_id.order_line.mapped('qty_delivered')) > 0:
            raise ValidationError("One of the product is delivered please return it first to proceed further!")
        else:
            self._split_and_action('hold')
        # sale_id = self.sale_order_id
        # pickings = sale_id.picking_ids
        # if any(pick.state == 'done' for pick in pickings):
        #     raise ValidationError("At least one of the picking is done please return it first to proceed")
        # self._split_and_action('hold')

    def split_and_cancel(self):
        if sum(self.sale_order_id.order_line.mapped('qty_delivered')) > 0:
            raise ValidationError("One of the product is delivered please return it first to proceed further!")
        else:
            self._split_and_action('cancel')

    def _split_and_action(self, action):
        sale_id = self.sale_order_id
        payload = self._split_line_vals_goflow()
        if payload:
            goflow_order_obj = self.env['goflow.order']
            go_flow_instance_obj = self.env['goflow.configuration'].search(
                [('active', '=', True), ('state', '=', 'done')],
                limit=1)
            goflow_order = goflow_order_obj.search([('sale_order_id', '=', sale_id.id)], limit=1)

            if goflow_order and go_flow_instance_obj:
                url = f"/v1/orders/{goflow_order.goflow_order_id}/splits"
                response = go_flow_instance_obj._send_goflow_request('post', url, payload=payload)
                if response.status_code == 200:
                    response = response.json()
                    orders = response.get('orders', [])
                    if len(orders)> 1:
                        self._cancel_current_sale(goflow_order)
                        old_order = orders[1]
                        new_order = orders[0]
                        if old_order:
                            exist_order = goflow_order_obj.search([('goflow_order_id', '=', old_order['id'])])
                            if not exist_order:
                                goflow_order_obj.create_goflow_order(old_order, go_flow_instance_obj)
                            old_order_brw = goflow_order_obj.search([('goflow_order_id', '=', old_order['id'])])
                            if old_order_brw.sale_order_id.state != "sale":
                                old_order_brw.sale_order_id.sudo().action_confirm()
                        if new_order:
                            exist_order = goflow_order_obj.search([('goflow_order_id', '=', new_order['id'])])
                            if not exist_order:
                                goflow_order_obj.create_goflow_order(new_order, go_flow_instance_obj)
                                # find new order
                                new_order_brw = goflow_order_obj.search([('goflow_order_id', '=', new_order['id'])])
                                if action == 'hold':
                                    new_order_brw.goflow_set_order_hold()
                                    if new_order_brw.sale_order_id.state == 'hold':
                                        new_order_brw.sale_order_id.sudo().message_post(
                                            body="New Goflow order Successfully set On Hold")
                                if action == 'cancel':
                                    new_order_brw.sale_order_id.with_context(disable_cancel_warning=True,
                                                                            salewizard=True).action_cancel()
                                    if new_order_brw.sale_order_id.state == 'cancel':
                                        new_order_brw.sale_order_id.sudo().message_post(
                                            body="New Goflow order Successfully Cancelled")

    def _cancel_current_sale(self, goflow_order):
        sale_id = self.sale_order_id
        sale_id.order_to_cancel(goflow_order)

    def _split_line_vals_goflow(self):
        sale_id = self.sale_order_id
        new_lines = []
        old_lines = []
        # vals = []
        for line in sale_id.order_line:
            new_line = self.order_line.filtered(lambda a: a.so_line_id.id == line.id)
            goflow_order_line_id = line.goflow_order_line_id
            if goflow_order_line_id:
                if new_line:
                    old_qty = line.product_uom_qty - new_line.product_qty
                    if old_qty > 0:
                        old_lines.append({
                            "id": str(goflow_order_line_id),
                            "quantity": int(old_qty)
                        })
                    new_lines.append({
                        "id": str(goflow_order_line_id),
                        "quantity": int(new_line.product_qty)
                    })
                    # vals.append(fields.Command.update(line.id, {'product_uom_qty': new_line.product_qty}))
                else:
                    old_lines.append({
                        "id": str(goflow_order_line_id),
                        "quantity": int(line.product_uom_qty)
                    })
                    # vals.append(fields.Command.update(line.id, {'product_uom_qty': 0}))
        data = {
            "chunks": [{"lines": old_lines}, {"lines": new_lines}]
        }
        # sale_id.sudo().write({'order_line': vals})
        return data


    # def split_and_hold(self):
    #     sale_id = self.sale_order_id
    #     defaults = {
    #         'order_line': [self.split_order_line_vals(line) for line in self.order_line]
    #     }
    #     copy_sale = sale_id.copy(defaults)
    #     sale_order_name = sale_id.name.split('-',1)
    #     if len(sale_order_name) > 1:
    #         name = f"{copy_sale.name}-{sale_order_name[1]}"
    #         copy_sale.update({'name': name})
    #     for line in self.order_line:
    #         remaining_qty = line.so_line_id.product_uom_qty - line.product_qty
    #         line.so_line_id.write({'product_uom_qty': remaining_qty})
    #     sale_id.write({'state': 'hold'})
    #     print(copy_sale)

    # def _split_order_line_vals(self, order_line):
    #     """
    #     Function to pass sale order lines values to create new split sale order.
    #     :param order_line: order line from wizard with custom qty.
    #     :return: line vals to be created in new sale order line.
    #     """
    #     return fields.Command.create({'product_id': order_line.product_id.id,
    #                                   'product_uom_qty': order_line.product_qty,
    #                                   'price_unit': order_line.price_unit,
    #                                   'product_uom': order_line.product_uom.id,
    #                                   })

    # def split_and_cancel(self):
    #     sale_id = self.sale_order_id
    #     defaults = {
    #         'order_line': [self.split_order_line_vals(line) for line in self.order_line]
    #     }
    #     copy_sale = sale_id.copy(defaults)
    #     sale_order_name = sale_id.name.split('-', 1)
    #     if len(sale_order_name) > 1:
    #         name = f"{copy_sale.name}-{sale_order_name[1]}"
    #         copy_sale.update({'name': name})
    #     for line in self.order_line:
    #         remaining_qty = line.so_line_id.product_uom_qty - line.product_qty
    #         line.so_line_id.write({'product_uom_qty': remaining_qty})
    #     sale_id.with_context(disable_cancel_warning=True).action_cancel()
