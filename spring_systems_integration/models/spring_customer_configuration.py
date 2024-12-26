# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SpringCustomerConfiguration(models.Model):
    _name = 'spring.customer.configuration'
    _description = 'Spring Customer Configuration'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string="Customer")
    spring_customer_id = fields.Char(string="Spring Customer Id")
    note = fields.Char(string="Note")
    receive_850 = fields.Boolean(string="Receive 850")
    send_855 = fields.Boolean(string="Send 855")
    send_856 = fields.Boolean(string="Send 856")
    send_810 = fields.Boolean(string="Send 810")