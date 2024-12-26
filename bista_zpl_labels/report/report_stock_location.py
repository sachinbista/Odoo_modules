# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import UserError


class StockLocation(models.AbstractModel):
    _name = "report.bista_zpl_labels.stock_location_label_template"
    _description = "report.stock_location_label_template"

    @api.model
    def _get_report_values(self, docids, data=None):
        location_ids = data.get("location_ids", [])
        if not location_ids:
            raise UserError("Nothing to print")

        label_id = data.get("label", False)
        if not label_id:
            raise UserError("You have not selected any label template.")

        locations = self.env['stock.location'].browse(location_ids)
        label = self.env['zpl.label'].browse(label_id)
        labels = "".join([label._get_label_date(line) for line in locations])
        return {
            'doc_model': 'stock.lot',
            'docs': locations,
            'value': labels
        }



