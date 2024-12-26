# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _
import requests
import json


class GoFLowPackingUpdateLog(models.Model):
    _name = 'go.flow.packaging.update.log'
    _description = 'Go Flow Packaging Info Update Log'

    name = fields.Char('Description')
    request_status = fields.Selection(
        [('sent_successfully', "Sent"), ('queuing_failed', "Queuing Failed"),
         ('doc_generated', "Completed"),
         ('doc_generated_not_uploaded', "Document Generated but not uploaded"),
         ('require_manual_shipment', "Updating Failed")],
        string="Request Status")
    schema = fields.Text('Schema')
    order_ref = fields.Char('Order Ref')
    order_name = fields.Char('Order Name')
    picking_id = fields.Many2one('stock.picking', string="picking")
    error = fields.Char('Error')

    def _send_order_packaging_info(self):
        flask_config = self.env['flask.server.config'].search([('active', '=', True)], limit=1)
        if flask_config:
            pickings = self.env['stock.picking'].search(
                [('state', '!=', 'done'), ('state', '!=', 'cancel'),
                 ('goflow_routing_status', '=', 'shipping_requested'), ('rpa_status', '=', False),('goflow_order_no','!=',False)],
                limit=7)
            for picking in pickings:
                rpa_process_type = list(set(picking.move_line_ids.mapped('rpa_process_type')))
                json_data = self.get_rp_process_json_data(picking, rpa_process_type)
                rpa_log_line_vals = {
                        'picking_id': picking.id,
                        'order_name': picking.origin,
                    }
                if json_data:
                   rpa_log_line_vals.update({
                    'schema': json_data,
                    })

                log_id = self.create(rpa_log_line_vals)
                if log_id and json_data:
                    log_id.make_api_request(json.dumps(json_data), flask_config)

    def make_api_request(self, json_data, flask_config):
        url = flask_config.url
        payload = json.dumps(json_data)
        headers = {
            'Authorization': flask_config.auth_token,
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                order_ref = json.loads(response.text).get('Ref')
                self.update({
                    'order_ref': order_ref,
                    'request_status': 'sent_successfully',
                    'error': False,
                })
                self.picking_id.update({
                    'rpa_status': True
                })
            else:
                self.update({
                    'error': response.text,
                    'request_status': 'queuing_failed'
                })
        except Exception as e:
            self.update({
                'error': e,
                'request_status': 'queuing_failed'
            })

    # def test_req(self):
    #     url = "http://127.0.0.1:5001/flybar/test"
    #     # url = "http://127.0.0.1:5000/api/post/data"
    #     # payload = json.dumps(json_data)
    #     headers = {
    #         'Authorization': 'qeyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.Bkh4aM2ILPEEh2O4RxllI43lqH5RySYhp_TH908IzLM',
    #         'Content-Type': 'application/json'
    #     }
    #     response = requests.request("GET", url, headers=headers)
    #     print(response)
    
    def get_rp_process_json_data(self,picking, rpa_process_type):
        json_data = {
        "order_name": picking.goflow_order_no,
        "weight": picking.total_weight,
        "length": picking.total_length,
        "width": picking.total_width,
        "height": picking.total_height,
        "picking": picking.id,
        "main_operation_type": picking.rpa_process_type,
        }
        for rp_type in rpa_process_type:
            vals_lst = []
            rpa_process_type_lines = picking.move_line_ids.filtered(
                lambda l: l.rpa_process_type == rp_type)
            line_package = []
            for line in rpa_process_type_lines:
                if line.result_package_id.id not in line_package:
                    line_package.append(line.result_package_id.id)
                    if rp_type !='split_multi_box':
                        line_dict = {
                            'package_name': line.result_package_id.name,
                            'box_type': line.result_package_id.package_type_id.name if line.result_package_id.package_type_id else '',
                            'weight': line.weight,
                            'length': line.product_length,
                            'width': line.product_width,
                            'height': line.product_height,
                        }
                    if rp_type =='split_multi_box':
                        line_dict = {
                            'product_name':line.product_id.default_code ,
                            'quantity': line.reserved_uom_qty,
                            'package_name': line.result_package_id.name,
                            'box_type': line.result_package_id.package_type_id.name if line.result_package_id.package_type_id else '',
                            'weight': line.weight,
                            'length': line.product_length,
                            'width': line.product_width,
                            'height': line.product_height,
                        }
                    elif rp_type in ('individual_item_same_box','individual_separate_multi_box'):
                        line_dict.update({
                            'product_lines': [{
                            'product_name': i.product_id.default_code, 
                            'quantity': i.reserved_uom_qty
                        } for i in picking.move_line_ids.filtered(lambda ml: ml.result_package_id.id == line.result_package_id.id)],
                        })
                    else:
                        pass
                    vals_lst.append(line_dict)
                
                    json_data.update({rp_type: vals_lst})
        print("json_data",json_data)
        return json_data

