# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json


class SaleOrder(models.Model):
    _inherit = "sale.order"

    external_so_id = fields.Integer(string='External Sale ID')
    external_origin = fields.Selection([
        ('spring_system', 'Spring System'),
        ('manual', 'Manual')], string='Origin', default='manual')


    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            if so.external_origin == 'spring_system':
                so.create_edi_855()
        return res

    def create_edi_855(self):
        edi_855_obj = self.env['spring.edi.855']
        edi_850_brw = self.env['spring.systems.sale.order'].search([('sale_order_id', '=', self.id)])
        edi_850_brw.update({'status': 'done'})
        edi_850_data = edi_850_brw.edi_850_data
        sale_json = eval(edi_850_data)
        sale_json.update({'po_acknowledge_status': 100})
        edi_855_obj.create({
            'spring_system_so_id': edi_850_brw.spring_system_so_id,
            'spring_system_vendor_num': edi_850_brw.spring_system_vendor_num,
            'spring_system_po_num': edi_850_brw.spring_system_po_num,
            'sale_order_id': edi_850_brw.sale_order_id.id,
            'payment_term': edi_850_brw.payment_term_id.name,
            'edi_855_data': str(sale_json),
            'status': 'draft',
        })