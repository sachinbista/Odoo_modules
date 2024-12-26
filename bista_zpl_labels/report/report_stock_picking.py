# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError


class StockQuantLabel(models.AbstractModel):
    _name = "report.bista_zpl_labels.stock_quant_label_template"
    _description = "report.stock_quant_label_template"

    @api.model
    def _get_report_values(self, docids, data=None):
        label = data.get('label', False)
        return {'value': label}
