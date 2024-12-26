# -*- coding: utf-8 -*-

from odoo import models, fields


class GoFlowOrder(models.Model):
    _name = 'goflow.vendor'
    _description = 'Goflow Vendor Data'
    _rec_name = 'name'

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    name = fields.Char(string='GoFlow Vendor Name')
    goflow_vendor_id = fields.Integer(string='Goflow Vendor ID')
    status = fields.Selection([('active', 'Active'), ('inactive', 'In Active')], string='Status')
    currency = fields.Many2one('res.currency')
    notes = fields.Text(string='Notes')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    vendor_data = fields.Text(string='JSON vendor Data')
    tags = fields.Many2many('res.partner.category', column1='goflow_vendor_id',
                            column2='category_id', string="Tags", default=_default_category)
    configuration_id = fields.Many2one('goflow.configuration', string='Instance')
