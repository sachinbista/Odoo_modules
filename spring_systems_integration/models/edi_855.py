# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SpringEdi855(models.Model):
    _name = 'spring.edi.855'
    _description = 'Spring Edi 855'


    spring_system_so_id = fields.Char(string='Spring System SO ID')
    spring_system_vendor_num = fields.Char(string='Spring System vendor Num')
    spring_system_po_num = fields.Char(string='Spring System po num')
    configuration_id = fields.Many2one('spring.systems.configuration', string='Instance')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')], string='Status')
    payment_term = fields.Char(string="Payment Terms")
    edi_855_data = fields.Text(string='Spring System SO Data')
    system_errors = fields.Text(string='Errors')


    def send_acknowledgement(self):
        po_list = []
        so_to_send = self.env['spring.edi.855'].search([('status', '=', 'draft')])
        po_new = {}
        for so in so_to_send:
            edi_855_data = eval(so.edi_855_data)
            po = {}
            sale_id = so.sale_order_id
            mark_for_location = edi_855_data.get('mark_for_location', '')
            if mark_for_location:
                po.update({'mark_for_location': mark_for_location})

            mark_for_location_id = edi_855_data.get('mark_for_location_id', '')
            if mark_for_location_id:
                po.update({'mark_for_location_id': mark_for_location_id})

            po_acknowledge_status = edi_855_data.get('po_acknowledge_status', '')
            if po_acknowledge_status:
                po.update({'po_acknowledge_status': po_acknowledge_status})

            po_additional = edi_855_data.get('po_additional', '')
            if po_additional:
                payment_terms = po_additional['attributes']['payment_terms']
                sale_payment_term = sale_id.payment_term_id
                if payment_terms and payment_terms['payment_term'] and payment_terms['payment_term'].get('payment_description') != sale_payment_term.name:
                    balance_line = sale_payment_term.line_ids.filtered(lambda x: x.value == 'balance')[0]
                    updated_payment_term = {'payment_days': str(balance_line.days), 'payment_days_basis_code': [], 'payment_days_basis_description': [],
                     'payment_description': sale_payment_term.name, 'payment_discount_days': [], 'payment_net_days': str(balance_line.days)}
                    payment_terms.update({'payment_term': updated_payment_term})
                po.update({'po_additional': po_additional})


            po_id = edi_855_data.get('po_id', '')
            if po_id:
                po.update({'po_id': po_id})

            po_original_num = edi_855_data.get('po_original_num', '')
            if po_original_num:
                po.update({'po_original_num': po_original_num})

            po_type = edi_855_data.get('po_type', '')
            if po_type:
                po.update({'po_type': po_type})

            po_items = edi_855_data.get('po_items', '')
            if po_items:
                po_lines = po_items.get('po_item', '')
                po_item = []
                if po_lines:
                    for sale_line in sale_id.order_line:
                        product_code = sale_line.product_id.default_code
                        line = list(filter(lambda item: item['product']['product_vendor_item_num'] == product_code, po_lines))[0]
                        attribute_changes = ''
                        if line.get('po_item_qty_confirmed', False) != sale_line.product_uom_qty:
                            line.update({'po_item_qty_confirmed': sale_line.product_uom_qty})
                        if line.get('po_item_unit_price_confirmed', False) != sale_line.price_unit:
                            line.update({'po_item_unit_price_confirmed': sale_line.price_unit})
                        po_item.append(line)
                po.update({'po_items': po_item})

            po_num = edi_855_data.get('po_num', '')
            if po_num:
                po.update({'po_num': po_num})

            po_original_num = edi_855_data.get('po_original_num', '')
            if po_original_num:
                po.update({'po_original_num': po_original_num})

            po_rel_num = edi_855_data.get('po_rel_num', '')
            if po_rel_num:
                po.update({'po_rel_num': po_rel_num})

            retailer = edi_855_data.get('retailer', '')
            if retailer:
                po.update({'retailer': retailer})

            retailer_id = edi_855_data.get('retailer_id', '')
            if retailer_id:
                po.update({'retailer_id': retailer_id})

            ship_from_location = edi_855_data.get('ship_from_location', '')
            if ship_from_location:
                po.update({'ship_from_location': ship_from_location})

            ship_to_location_id = edi_855_data.get('ship_to_location_id', '')
            if ship_to_location_id:
                po.update({'ship_to_location_id': ship_to_location_id})

            vendor = edi_855_data.get('vendor', '')
            if vendor:
                po.update({'vendor': vendor})

            vendor_id = edi_855_data.get('vendor_id', '')
            if vendor_id:
                po.update({'vendor_id': vendor_id})
            po_list.append(po)
        po_new.update({'pos':{'po': po_list}})
        print(po_new)

        config_id = self.env['spring.systems.configuration'].search([])
        for config in config_id:
            connection_url = (config.url + 'acknowledgement-incoming/send/api_user/' +
                              config.api_user + '/api_key/' + config.api_key)

            response = config._send_spring_request('post', connection_url, payload=po_new)
            if response and response.status_code == 200:
                print('yes')

