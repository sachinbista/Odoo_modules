# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SpringEdi810(models.Model):
    _name = 'spring.edi.810'
    _description = 'Spring Edi 810'


    spring_system_so_id = fields.Char(string='Spring System SO ID')
    spring_system_invoice_id = fields.Char(string='Spring System SO ID')
    spring_system_vendor_num = fields.Char(string='Spring System vendor Num')
    spring_system_po_num = fields.Char(string='Spring System po num')
    configuration_id = fields.Many2one('spring.systems.configuration', string='Instance')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')], string='Status')
    payment_term = fields.Char(string="Payment Terms")
    edi_810_data = fields.Text(string='Spring System Invoice Data')
    edi_810_response_data = fields.Text(string='Spring System Invoice Data')
    edi_850_data = fields.Text(string='Spring System SO Data')
    system_errors = fields.Text(string='Errors')