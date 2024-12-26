# -*- coding: utf-8 -*-
from odoo import models, fields, api, _,Command
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    external_origin = fields.Selection([
        ('manual', 'Manual'),
        ('go_flow', 'Go Flow'),
        ('spring_system', 'Spring System'),
        ('market_time', 'Market Time')], string='Order From', default='manual', readonly=True, store=True, copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    po_ref_updated = fields.Boolean(default=False)
    po_ref_updated_try = fields.Integer(default=0)

    def cron_to_update_po_ref(self, limit=None,try_again=0):
        if limit == None:
            limit = 10
        order_names = self.sudo().search([('external_origin', '=', 'go_flow'), ('po_ref_updated', '=', False),('po_ref_updated_try','=',try_again)],limit=limit, order='invoice_date asc').mapped('ref')
        sale_orders = self.env['sale.order'].sudo().search([('name', 'in', order_names), ('invoice_status', '=', 'invoiced')])

        filter = ''
        count = 0
        for order in sale_orders:
            if count == 0:
                filter += "?filters[id]=" + str(order.origin)
            else:
                filter += "&filters[id]=" + str(order.origin)

            count += 1

        if filter:
            go_flow_instance = self.env['goflow.configuration'].sudo().search([('active', '=', True), ('state', '=', 'done'), ('sale_order_import_operation', '=', True)])
            url = '/v1/orders' + filter
            goflow_order_response = go_flow_instance.sudo()._send_goflow_request('get', url)
            goflow_order_obj = self.env['goflow.order']
            if goflow_order_response:

                goflow_order_response = goflow_order_response.json()
                orders = goflow_order_response.get("data", [])
                next_orders = goflow_order_response.get("next", '')
                if orders:
                    for order in orders:
                        exist_order = goflow_order_obj.sudo().search([('goflow_order_id', '=', order['id'])])
                        if 'invoice_number' in order:
                            if exist_order and order['invoice_number'] != None:
                                exist_order.sale_order_id.invoice_ids.sudo().update({'po_reference': order['invoice_number'], 'po_ref_updated': True})
                        else:
                            exist_order.sale_order_id.invoice_ids.sudo().update({'po_ref_updated_try': try_again + 1})




class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    # added to set goflow "order from" from sale order to invoice.
    def _create_invoices(self, sale_order):
        self.ensure_one()
        sale_order.ensure_one()
        result = super(SaleAdvancePaymentInv, self)._create_invoices(sale_order)
        for invoice in result:
            if sale_order.external_origin:
                invoice.update({'external_origin': sale_order.external_origin})
        return result