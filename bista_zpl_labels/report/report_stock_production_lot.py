# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError


class StockLotLabel(models.AbstractModel):
    _name = "report.bista_zpl_labels.stock_lot_label"
    _description = "report.stock_lot_label"

    @api.model
    def _get_report_values(self, docids, data=None):
        lot_ids = data.get("lot_ids", [])
        if not lot_ids:
            raise UserError("Nothing to print.")

        label_id = data.get("label", False)
        if not label_id:
            raise UserError("You have not selected any label template.")

        lots = self.env['stock.lot'].browse(lot_ids)
        label = self.env['zpl.label'].browse(label_id)
        labels = "".join([label._get_label_date(line) for line in lots])
        return {
            'doc_model': 'stock.lot',
            'docs': lot_ids,
            'value': labels
        }
