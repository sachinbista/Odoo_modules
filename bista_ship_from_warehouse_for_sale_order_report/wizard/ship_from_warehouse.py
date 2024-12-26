# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo.exceptions import ValidationError

from odoo import models, fields, _


class ShipFromWarehouseReport(models.TransientModel):
    _name = 'ship.from.warehouse.report'
    _description = "Ship From Warehouse"

    def _get_warehouse_domain(self):
        company_ids = self.env['res.company'].search([('ship_from_warehouse', '=', True)]).ids or []
        return [('company_id', 'in', company_ids)]

    warehouse_id = fields.Many2one("stock.warehouse", "Warehouse", domain=_get_warehouse_domain)

    def change_order_warehouse(self):
        active_ids = self.env.context.get('active_ids')
        order_ids = self.env['sale.line.report'].browse(active_ids or [])
        message = ""
        no_matching_wh_orders = []
        done_picking_order = []
        confirmed_order_ids = []
        non_confirmed_orders = []

        for order in order_ids:

            if order.company_id and not order.company_id.ship_from_warehouse:
                no_matching_wh_orders.append(order.name)
            else:
                if order.order_id.state not in ['sale']:
                    non_confirmed_orders.append(order.name)

                done_pickings = order.order_id.picking_ids.filtered(lambda picking: picking.state == 'done')
                matching_return_pickings = order.order_id.picking_ids.filtered(
                    lambda picking: any(
                        picking.origin == f"Return of {done_picking.name}" for done_picking in done_pickings)
                )

                if order.order_id.picking_ids and order.order_id.picking_ids.filtered(
                        lambda picking: picking.state == 'done').ids and not matching_return_pickings:
                    done_picking_order.append(order.name)

                else:
                    confirmed_order_ids.append(order.order_id.id)


        if no_matching_wh_orders:
            message += _("- Below order(s) do not belong to Flybar company.") + "\n" + ',  '.join(
                map(str, no_matching_wh_orders)) + "\n\n"
        if non_confirmed_orders:
            message += _("- Below order(s) are not confirmed.") + "\n" + ',  '.join(
                map(str, non_confirmed_orders)) + "\n\n"
        if done_picking_order:
            message += _("- Pickings for below order(s) are already done.") + "\n" + ',  '.join(
                map(str, done_picking_order)) + "\n\n"

        if message:
            raise ValidationError(message)
        else:
            confirmed_orders = self.env['sale.order'].browse(confirmed_order_ids).filtered(
                lambda order: order.warehouse_id.id != self.warehouse_id.id)

            # Cancel pickings and update warehouse
            done_pickings = confirmed_orders.picking_ids.filtered(lambda picking: picking.state == 'done')
            matching_return_pickings = confirmed_orders.picking_ids.filtered(
                lambda picking: any(
                    picking.origin == f"Return of {done_picking.name}" for done_picking in done_pickings)
            )

            pickings_to_cancel = confirmed_orders.picking_ids.filtered(
                lambda picking: picking.state != 'done' and picking not in matching_return_pickings)
            pickings_to_cancel.action_cancel()
            confirmed_orders.update({'warehouse_id': self.warehouse_id.id})
            confirmed_orders.action_confirm()
            sale_line_report_ids = self.env['sale.line.report'].search([('order_id', 'in', confirmed_orders.ids)])
            sale_line_report_ids.write({'picking_id': confirmed_orders.mapped('picking_ids').filtered(
                lambda s: s.state != "cancel" and s.picking_type_id.code == 'outgoing')})
