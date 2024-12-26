# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, models, fields, _
import requests
from odoo.exceptions import ValidationError


class RithumErrorOrderLog(models.Model):
    _name = 'rithum.error.order.log'
    _description = "Rithum Orders Import Error"

    name = fields.Char("Name")
    error_date = fields.Date('Date')
    error_message = fields.Char("Error Message")
    rithum_config_id = fields.Many2one('rithum.config', string="Rithum Config ID")
    active = fields.Boolean(default=True)

    def import_rithum_order(self):
        for rec in self:
            if rec.rithum_config_id:
                res = rec.rithum_config_id.with_context(from_error=True).create_orders_single_order(rec.name)
                if res:
                    rec.unlink()

class RithumErrorInvoiceLog(models.Model):
    _name = 'rithum.error.invoice.log'
    _description = "Rithum Invoice Import Error"

    name = fields.Char("Invoice Number")
    po_number = fields.Char("Po Number")
    error_date = fields.Date('Date')
    error_message = fields.Char("Error Message")
    rithum_config_id = fields.Many2one('rithum.config', string="Rithum Config ID")

class RithumErrorInventoryLog(models.Model):
    _name = 'rithum.error.inventory.log'
    _description = "Rithum Inventory Import Error"

    name = fields.Char("Error Code")
    error_date = fields.Datetime('Date')
    error_message = fields.Char("Error Message")
    rithum_config_id = fields.Many2one('rithum.config', string="Rithum Config ID")

