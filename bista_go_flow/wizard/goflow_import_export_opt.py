# -*- coding: utf-8 -*-

from odoo import models, fields, api

class GoFlowImportExportOpt(models.TransientModel):
    _name = 'goflow.import.export.opt'
    _description = 'Goflow Import Export opt'

    instance_id = fields.Many2one(comodel_name='goflow.configuration',
        string='Instances', domain="[('state', '=', 'done')]")
    operations = fields.Selection([('import_channel', 'Import Channel'), ('import_sale_order', 'Import Sale Order'),
                                          ('import_products', 'Import Products'), ('export_tracking_information', 'Export Shipment Information'),
                                          ('import_warehouse', 'Import Warehouse'), ('export_product_stock', 'Export Product Stock')],
                                         string='Import/ Export Operations')

    def execute(self):
        return True