# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowProductMapLine(models.Model):
    _name = 'goflow.product.map.line'
    _description = 'GoFlow Product Map Line'

    goflow_configuration_id = fields.Many2one('goflow.configuration')
    sequence = fields.Integer(string='Sequence')
    display_goflow_field = fields.Selection([
        ('name', 'Name'),
        ('upc', 'UPC'),
        ('sku', 'SKU')], string='Display Goflow Fields')
    mapping_opt = fields.Selection([
        ('like', 'Like'),
        ('like_per', '%Like%')], string='Map Fields with')
    display_odoo_fields = fields.Many2many('ir.model.fields', string="Display odoo Fields")


