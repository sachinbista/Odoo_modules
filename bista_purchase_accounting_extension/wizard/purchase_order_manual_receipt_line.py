# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import re



class PurchaseOrderManualReceiptLine(models.TransientModel):
    _inherit = 'purchase.order.manual.receipt.line'


    def create_entries(self):
        res_config_obj = self.env['ir.config_parameter'].sudo()
        good_shipped_acc_id = res_config_obj.get_param('good_shipped_acc_id', default=False)
        bs_po_good_shipped_id = res_config_obj.get_param('bs_po_good_shipped_id', default=False)
        match = re.search(r'\((\d+),\)', bs_po_good_shipped_id)
        bs_po_good_shipped_id_value = int(match.group(1)) if match else None
        if good_shipped_acc_id and bs_po_good_shipped_id:
            for po_line in self.filtered(lambda line: line.unit_price != 0 and line.product_id.detailed_type == 'product'
                                                    and line.product_id.categ_id.property_valuation != 'manual_periodic'):
                cost = po_line.product_uom_qty * po_line.unit_price
                description = po_line.purchase_line_id.order_id.name + "- " + po_line.manual_receipt_id.container_id if po_line.manual_receipt_id.container_id else po_line.purchase_line_id.order_id.name
                po_line.purchase_line_id.with_context({'inv_reference': po_line.manual_receipt_id.inv_reference,'date': po_line.manual_receipt_id.inv_date if po_line.manual_receipt_id.inv_date  else fields.Date.context_today(self)})._account_entry_move(po_line.product_uom_qty,description, cost,int(good_shipped_acc_id),bs_po_good_shipped_id_value)