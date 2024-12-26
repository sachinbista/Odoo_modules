# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class SpringSystemProduct(models.Model):
    _name = 'spring.system.product'
    _description = 'Spring System Product'

    name = fields.Char(string='Spring Product Name')
    item_number = fields.Char(string='Spring Product Item No')
    product_external_id = fields.Integer(string='Spring Product ID')
    product_id = fields.Many2one('product.product', string='Product')
    type = fields.Selection([
        ('group', 'Group'),
        ('kit', 'Kit'),
        ('standard', 'Standard')], string='Product Type')
    configuration_id = fields.Many2one('spring.systems.configuration', string='Instance')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')], string='Status')
    data = fields.Text(string='Spring Product Data')
    info = fields.Text(string='Spring Product Info')
    create_update_in_spring_system = fields.Boolean(string='To be Created/Updated In Spring')
    create_update_in_odoo = fields.Boolean(string='To be Created/Updated In Odoo')


class SpringSystemsConfiguration(models.Model):
    _inherit = 'spring.systems.configuration'

    state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('done', 'Confirmed')], string='State', default='draft')
    sync_product = fields.Boolean(string="Auto Product syn",default=True)