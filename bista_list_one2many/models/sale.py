import logging
from datetime import datetime
from operator import itemgetter
from werkzeug.urls import url_encode
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class SaleOrder(models.Model):
    _inherit = 'sale.sub.line.report'

    # display_warehouse_qty_widget = fields.Boolean(default=False)
    # display_qty_widget = fields.Boolean(default=False)
    move_ids = fields.One2many('stock.move', 'sale_line_id', string='Stock Moves')
    move_id = fields.Many2one('stock.move', 'Move', readonly=True)
    scheduled_date = fields.Date(related='line_report_id.scheduled_date')
