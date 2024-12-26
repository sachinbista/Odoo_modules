# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        #inherit of the function from account.move to send edi810
        res = super(AccountMove, self).action_post()
        self.create_edi_810()
        return res

    def create_edi_810(self):
        edi_810_obj = self.env['spring.edi.810']
        sale_id = self.env['sale.order'].search([('invoice_ids', 'in', self.ids), ('external_origin', '=', 'spring_system')])
        if sale_id:
            edi_850_brw = self.env['spring.systems.sale.order'].search([('sale_order_id', '=', sale_id.id)])
            edi_856_brw = self.env['spring.edi.856'].search([('sale_order_id', '=', sale_id.id)])
            edi_850_str = edi_850_brw.edi_850_data
            edi_850_data = eval(edi_850_str)
            if edi_856_brw:
                ship_date = edi_856_brw.picking_id.scheduled_date
            else:
                ship_date = sale_id.effective_date
            invoices = {}
            invoice = []
            edi_810_vals = {'vendor_id': edi_850_data.get('vendor_id'),
                            'retailer_id': edi_850_data.get('retailer_id'),
                            'invoice_amount': self.amount_total,
                            'invoice_additional': {
                                    'attributes': {
                                        'invoice_date': str(self.invoice_date.strftime("%Y-%m-%d")),
                                        'ship_info_ship_date': str(ship_date.strftime("%Y-%m-%d"))
                                    }
                                },
                            }
            invoice_po = []
            po_items = edi_850_data['po_items']['po_item']
            for move_line in self.invoice_line_ids:
                product_code = move_line.product_id.default_code
                item_line = list(filter(lambda item: item['product']['product_vendor_item_num'] == product_code, po_items))[0]
                invoice_po_vals = {
                    'po_id': edi_850_data.get('po_id'),
                    'invoice_po_item': { 'po_item_id':item_line.get('po_item_id'),
                                         'invoice_po_item_price': move_line.price_total,
                                         'invoice_po_item_qty': move_line.quantity},
                               }
                invoice_po.append(invoice_po_vals)
            edi_810_vals.update({'invoice_po': invoice_po})
            invoice.append(edi_810_vals)
            invoices.update({'invoice': invoice})
            end_vals = {'invoices': invoices}
            config_id = self.env['spring.systems.configuration'].search([])
            for config in config_id:
                connection_url = (config.url + 'invoice-incoming/send/api_user/' +
                                  config.api_user + '/api_key/' + config.api_key)
                response = config._send_spring_request('post', connection_url, payload=end_vals)
                if response and response.status_code == 200:
                    edi_810_obj.create({
                        'edi_810_data': str(end_vals),
                        'status': 'posted',
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
