# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import ValidationError

import string


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    stock_transfer_id = fields.Many2one('inter.company.stock.transfer', 'Stock Transfer')

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({'ref': self.name})
        return invoice_vals

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda rec: rec.state not in ('done', 'cancel'))
            # goflow_routing_status = ""
            # if order.goflow_store_id.require_manual_shipment or order.goflow_shipment_type in ['ltl','pickup']:
            #     goflow_routing_status = 'require_manual_shipment'
            goflow_order_rec = self.env['goflow.order'].sudo().search([
                ('sale_order_id', '=', order.id)])
            picking_vals = {
                'intercom_sale_order_id': order.id,
                'external_origin': order.external_origin,
                'goflow_customer_name': order.goflow_customer_name,
                'goflow_street1': order.goflow_street1,
                'goflow_street2': order.goflow_street2,
                'goflow_city': order.goflow_city,
                'goflow_state': order.goflow_state,
                'goflow_zip_code': order.goflow_zip_code,
                'goflow_country_code': order.goflow_country_code,
                'goflow_shipment_type': order.goflow_shipment_type,
                'goflow_carrier': order.goflow_carrier,
                'goflow_shipping_method': order.goflow_shipping_method,
                'goflow_scac': order.goflow_scac,
                'goflow_shipped_at': order.goflow_shipped_at,
                'goflow_currency_code': order.goflow_currency_code,
                'goflow_order_id': goflow_order_rec and goflow_order_rec.goflow_order_id or False,
                'goflow_order_no': goflow_order_rec and goflow_order_rec.order_number or False,
                # 'goflow_routing_status': goflow_routing_status,
            }
            if order.warehouse_id and order.warehouse_id.sudo().resupply_warehouse_id:
                order.sudo().create_validate_stock_transfer()
                stock_transfer_id = order.stock_transfer_id
                if stock_transfer_id:
                    stock_transfer_ref = """<a href=# data-oe-model=inter.company.stock.transfer 
                                            data-oe-id=%s>%s</a>""" % (stock_transfer_id.id, stock_transfer_id.name)
                    pickings.message_post(
                        body='Inter-company stock transfer is created for this transfer with reference: %s' % stock_transfer_ref)
            if order.goflow_carrier:
                goflow_carrier = order.goflow_carrier
                # ascii_numbers = string.ascii_letters + string.digits
                # goflow_carrier = ''.join(c for c in goflow_carrier if c in ascii_numbers).lower()
                carrier_ids = self.env['delivery.carrier'].sudo().search([('carrier_code', '=', goflow_carrier)])
                carrier_id = False
                for carrier in carrier_ids:
                    carrier_name = carrier.carrier_code
                    if goflow_carrier == carrier_name:
                        carrier_id = carrier.id
                picking_vals.update({'carrier_id': carrier_id})
            pickings.write(picking_vals)
        return res

    def action_cancel(self):
        for rec in self:
            if rec.stock_transfer_id:
                if any(rec.stock_transfer_id.sudo().picking_ids.filtered(lambda p: p.state == 'done')):
                    raise ValidationError(_("You are not allowed to cancel the order if any picking is done."))
                else:
                    rec.stock_transfer_id.sudo().action_cancel()
        res = super(SaleOrder, self).action_cancel()
        return res

    def create_validate_stock_transfer(self):
        for rec in self:
            ctx = dict(self._context)
            ctx.update({'sale_stock_transfer': True, 'sale_order_ref': rec})
            dest_warehouse_id = rec.warehouse_id
            if not dest_warehouse_id:
                raise ValidationError(_('Warehouse is not defined in sale order.'))
            goflow_warehouse = self.env['goflow.warehouse'].search([('goflow_warehouse_name','=',rec.goflow_warehouse)], limit=1)
            src_warehouse_id = goflow_warehouse.warehouse_id if goflow_warehouse else dest_warehouse_id.sudo().resupply_warehouse_id
            if not src_warehouse_id:
                raise ValidationError(_(
                    F'Resupply Warehouse is not defined for warehouse {dest_warehouse_id.name}.'))
            src_company_id = src_warehouse_id.company_id
            dest_company_id = dest_warehouse_id.company_id
            transfer_line_ids = []
            for line in rec.order_line:
                is_single_ship = False
                product_volume = line.product_id.volume
                product_inventory_volume = self.env['ir.config_parameter'].sudo().get_param(
                    'sale_stock_extend.product_inventory_volume')
                if product_volume > 0 and product_volume > int(
                        product_inventory_volume) and rec.total_product_uom_qty < 7:
                    is_single_ship = True
                transfer_line_ids.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom and line.product_uom.id,
                    'product_uom_qty': line.product_uom_qty,
                    'is_single_ship': is_single_ship
                    }))

            stock_transfer_id = self.env['inter.company.stock.transfer'].sudo().create({
                'transfer_type': 'inter_company',
                'user_id': 2,
                'state': 'draft',
                'scheduled_date': rec.date_order,
                'exp_arrival_date': rec.date_order,
                'company_id': src_company_id and src_company_id.id or False,
                'dest_company_id': dest_company_id and dest_company_id.id or False,
                'warehouse_id': src_warehouse_id and src_warehouse_id.id or False,
                'dest_warehouse_id': dest_warehouse_id and dest_warehouse_id.id or False,
                'sale_order_id': rec.id,
                'origin': rec.name,
                'line_ids': transfer_line_ids
            })
            stock_transfer_id.with_context(ctx).sudo().action_validate()
            rec.stock_transfer_id = stock_transfer_id.id
            stock_transfer_ref = """<a href=# data-oe-model=inter.company.stock.transfer 
                        data-oe-id=%s>%s</a>""" % (stock_transfer_id.id, stock_transfer_id.name)
            rec.sudo().message_post(
                body='Inter-company stock transfer created successfully with reference: %s' % stock_transfer_ref)
