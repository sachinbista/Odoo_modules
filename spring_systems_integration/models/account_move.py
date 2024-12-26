# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        #inherit of the function from account.move to send edi810
        res = super(AccountMove, self).action_post()
        self.create_edi_810()
        return res

    def create_edi_810(self):
        edi_810_obj = self.env['spring.edi.810']
        sale_id = self.env['sale.order'].search([('invoice_ids', 'in', self.ids),
                                                 ('external_origin', '=', 'spring_system')])
        if sale_id:
            edi_850_brw = self.env['spring.systems.sale.order'].search([('sale_order_id', '=', sale_id.id)])
            edi_856_brw = self.env['spring.edi.856'].search([('sale_order_id', '=', sale_id.id)])
            edi_850_str = edi_850_brw.edi_850_data
            edi_850_data = eval(edi_850_str)
            ship_info_shipping_pay_method, ship_info_tracking, ship_date = '', '', ''
            if edi_856_brw:
                ship_date = edi_856_brw.picking_id.scheduled_date.strftime("%Y-%m-%d")
                edi_856_data = eval(edi_856_brw.edi_856_data)
                if edi_856_data:
                    ship_info = edi_856_data.get('ship_info', {})
                    ship_date = ship_info.get('ship_info_ship_date', '')
                    ship_info_additional = ship_info.get('ship_info_additional', {})
                    attributes = ship_info_additional.get('attributes', {})
                    ship_info_shipping_pay_method = attributes.get('ship_info_shipping_pay_method', '')
                    ship_info_tracking = ship_info.get('ship_info_tracking', '')
            else:
                ship_date = sale_id.effective_date.strftime("%Y-%m-%d")
            invoices = {}
            invoice = []
            edi_810_vals = {'vendor_id': edi_850_data.get('vendor_id'),
                            'retailer_id': edi_850_data.get('retailer_id'),
                            'invoice_amount': self.amount_total,
                            'invoice_additional': {
                                    'attributes': {
                                        'ship_info_shipping_pay_method': ship_info_shipping_pay_method,
                                        'ship_info_tracking': ship_info_tracking,
                                        'invoice_date': str(self.invoice_date.strftime("%Y-%m-%d")),
                                        'ship_info_ship_date': str(ship_date)
                                    }
                                },
                            'invoice_po': [{
                                'po_id': edi_850_data.get('po_id'),
                                "invoice_po_item": self._get_810_invoice_line_vals(edi_850_data)
                            }],
                            }
            invoice.append(edi_810_vals)
            invoices.update({'invoice': invoice})
            end_vals = {'invoices': invoices}
            config_id = self.env['spring.systems.configuration'].search([])
            for config in config_id:
                connection_url = (config.url + 'invoice-incoming/send/api_user/' +
                                  config.api_user + '/api_key/' + config.api_key)
                response = config._send_spring_request('post', connection_url, payload=end_vals)
                if response and response.status_code == 200:
                    response_data = json.loads(response.text)
                    invoice_response = response_data['invoices']['invoice'][0]
                    edi_810_obj.create({
                        'edi_810_data': str(end_vals),
                        'status': 'posted',
                        'edi_810_response_data': str(invoice_response),
                        'spring_system_invoice_id': invoice_response.get('invoice_id', ''),
                        'sale_order_id': sale_id.id,
                        'invoice_id': self.id
                    })
                else:
                    edi_810_obj.create({
                        'edi_810_data': str(end_vals),
                        'status': 'draft',
                        'sale_order_id': sale_id.id,
                        'invoice_id': self.id
                    })


    def _get_810_invoice_line_vals(self, edi_850_data):
        invoice_po_item = []
        po_items = edi_850_data['po_items']['po_item']
        for move_line in self.invoice_line_ids:
            product_code = move_line.product_id.default_code
            item_line = list(filter(lambda item: item['product']['product_vendor_item_num'] == product_code, po_items))[
                0]
            po_item = {
            'po_item_id': item_line.get('po_item_id'),
            'invoice_po_item_price': move_line.price_unit,
            'invoice_po_item_qty': move_line.quantity}
            invoice_po_item.append(po_item)
        return invoice_po_item
