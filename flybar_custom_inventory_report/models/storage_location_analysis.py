from odoo import tools
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class StorageLocationAnalysis(models.Model):
    _name = "storage.location.analysis"
    _rec_name = "location_id"
    _description = "Storage Location Analysis"

    location_id = fields.Many2one('stock.location', string="Location")
    storage_capacity = fields.Float(string="Storage Capacity")
    stock_qty = fields.Float(string="Stock Qty")
    storage_volume = fields.Float(string="Storage Volume")
    stock_volume = fields.Float(string="Stock Volume")

class StockLocation(models.Model):
    _inherit = "stock.location"

    storage_capacity = fields.Float(string="Storage Capacity")
    stock_qty = fields.Float(string="Available Qty")
    stock_volume = fields.Float(string="Stock Volume")
    stock_availability = fields.Float(string="Space Status")
    total_case_count = fields.Float(string="Total Case Count")
    total_pallet_count = fields.Float(string="Total Pallet Count")

