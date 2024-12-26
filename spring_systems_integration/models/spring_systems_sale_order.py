# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SpringSystemsSaleOrder(models.Model):
    _name = 'spring.systems.sale.order'
    _description = 'Spring Systems Sale Order'
    _rec_name = 'spring_system_so_id'
    _order = 'id'


    spring_system_so_id = fields.Char(string='Spring System SO ID')
    spring_system_vendor_num = fields.Char(string='Spring System vendor Num')
    spring_system_po_num = fields.Char(string='Spring System po num')
    configuration_id = fields.Many2one('spring.systems.configuration', string='Instance')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], string='Status')
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    edi_850_data = fields.Text(string='Spring System SO Data')
    system_errors = fields.Text(string='Errors')
