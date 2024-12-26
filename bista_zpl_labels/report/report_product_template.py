# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import UserError


class ReportProductTemplate(models.AbstractModel):
    _name = "report.bista_zpl_labels.product_template_label_template"
    _description = "report.product_template_label_template"

    @api.model
    def _get_report_values(self, docids, data=None):
        label_id = data.get("label", False)

        if not label_id:
            raise UserError("You have not selected any label template.")

        product_ids = data.get("product_ids", [])
        if not product_ids:
            raise UserError("Nothing to print.")

        product_obj = self.env['product.template']
        products = product_obj.browse(product_ids)
        label = self.env['zpl.label'].browse(label_id)
        labels = "".join([label._get_label_date(line) for line in products])
        return {
            'doc_model': 'product.template',
            'docs': product_ids,
            'value': labels
        }
