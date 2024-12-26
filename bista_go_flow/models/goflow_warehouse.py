# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowWarehouse(models.Model):
    _name = 'goflow.warehouse'
    _description = 'GoFlow Warehouse'

    goflow_warehouse_name = fields.Char(string='GoFlow Warehouse Name')
    goflow_warehouse_id = fields.Char(string='GoFlow Warehouse ID')
    configuration_id = fields.Many2one('goflow.configuration', string='Instance')
    company_id = fields.Many2one('res.company', string='Company')
    export_inventory_method = fields.Selection([
        ('on_hand', 'On Hand'),
        ('forecasted', 'Forecasted'),
        ('available', 'Available'),
        ('skip_upload_inventory', 'Skip Upload Inventory')], string='Stock Levels')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_type = fields.Char(string='Type')
    partner_id = fields.Many2one('res.partner', string='Address')
    goflow_warehouse_data = fields.Text(string='GoFlow Warehouse Downloaded Data')

    is_sync_goflow_inventory = fields.Boolean(string="Sync Goflow Inventory")
    goflow_sync_shipment = fields.Boolean(string="Sync Shipment?")
    goflow_get_document = fields.Boolean(string="Get Documents?")
