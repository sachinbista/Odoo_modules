# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import json

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        # goflow api calling
        res = super(StockQuant, self).action_apply_inventory()
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        product_warehouse_qty_obj = self.env['product.warehouse.quantity']
        if go_flow_instance_obj:
            for quant in self:
                # quant.post_go_flow_inv_adj(quant.location_id.warehouse_id,quant.product_id,quant.inventory_quantity,quant.display_name)
                product_id = quant.product_id
                warehouse_id = quant.location_id.warehouse_id
                product_warehouse_qty = product_warehouse_qty_obj.search([('product_id', '=', product_id.id),('warehouse_id', '=', warehouse_id.id)])
                on_hand_quantity = quant.product_id.with_context(warehouse=warehouse_id.id).qty_available
                goflow_product = self.env['goflow.product'].search([('product_id', '=', product_id.id)], limit=1)
                goflow_sync = False
                if goflow_product:
                    goflow_sync = True
                if product_warehouse_qty:
                    product_warehouse_qty.write({
                        'on_hand_quantity': on_hand_quantity,
                        'goflow_sync': goflow_sync
                    })
                else:
                    product_warehouse_qty_obj.create({
                        'product_id': quant.product_id.id,
                        'warehouse_id': quant.location_id.warehouse_id.id,
                        'on_hand_quantity': on_hand_quantity,
                        'goflow_sync': goflow_sync
                    })
        return res

    def post_go_flow_inv_adj(self,warehouse_id,product_id,qty,ref_no):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        if go_flow_instance_obj:
            lines = []
            goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id','=',warehouse_id.id)],limit=1)
            if goflow_warehouse.is_sync_goflow_inventory:
                goflow_product = self.env['goflow.product'].search([('product_id','=',product_id.id)],limit=1)
                if goflow_product:
                    lines.append({
                        "product_id": goflow_product.product_external_id,
                        "quantity": int(qty),
                        "cost": float(product_id.standard_price),
                        "reason": "Inventory Adjustment created from Odoo"
                    })
                data = {}
                if goflow_warehouse and lines:
                    data = {
                        "type": "absolute",
                        "warehouse_id": str(goflow_warehouse.goflow_warehouse_id),
                        "reference_number": str(ref_no),
                        "lines": lines
                    }
                    response = go_flow_instance_obj._send_goflow_request('post', '/v1/inventory/adjustments', payload=data)
                    # print("\nResponse::::::::::::::::::::",response.status_code)
                    # if response:
                    #     response = response.json()
                else:
                    print("warehouse, Product ",warehouse_id, product_id, qty, ref_no)
                    logging.warning("No GoFlow Warehouse found!")

class ProductWarehouseQuantity(models.Model):
    _name = 'product.warehouse.quantity'

    product_id = fields.Many2one("product.product", "Product")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    on_hand_quantity = fields.Integer()
    goflow_sync = fields.Boolean()


    def cron_product_warehouse_quantity_goflow(self):
        product_warehouse_records = self.env['product.warehouse.quantity'].sudo().search([('goflow_sync', '=', True)], limit=10, order='write_date asc')
        for rec in product_warehouse_records:
            warehouse_id = rec.warehouse_id
            product_id = rec.product_id
            qty = rec.on_hand_quantity
            ref_no = product_id.default_code

            go_flow_instance_obj = self.env['goflow.configuration'].sudo().search([('active', '=', True), ('state', '=', 'done')], limit=1)
            if go_flow_instance_obj:
                lines = []
                goflow_warehouse = self.env['goflow.warehouse'].sudo().search([('warehouse_id', '=', warehouse_id.id)], limit=1)
                if goflow_warehouse.is_sync_goflow_inventory:
                    goflow_product = self.env['goflow.product'].sudo().search([('product_id', '=', product_id.id)], limit=1)
                    if goflow_product:
                        lines.append({
                            "product_id": goflow_product.product_external_id,
                            "quantity": int(qty),
                            # "cost": float(product_id.standard_price),
                            "reason": "Inventory Adjustment created from Odoo"
                        })
                    data = {}
                    if goflow_warehouse and lines:
                        data = {
                            "type": "absolute",
                            "warehouse_id": str(goflow_warehouse.goflow_warehouse_id),
                            "reference_number": str(ref_no),
                            "lines": lines
                        }
                        response = go_flow_instance_obj.sudo()._send_goflow_request('post', '/v1/inventory/adjustments',payload=data)
                        if response.status_code in [200,201,204]:
                            rec.goflow_sync = False
                        # print("\nResponse::::::::::::::::::::",response.status_code)
                        # if response:
                        #     response = response.json()
                    else:
                        rec.goflow_sync = False
                        logging.warning("No GoFlow Warehouse found!")