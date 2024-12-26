from odoo import api, fields, models, _
import xlwt
from io import BytesIO
import base64
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ViewReport(models.TransientModel):
    _name = "view.report"
    _description = "View Report"

    file = fields.Binary('File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)


class PurchaseExceptionReport(models.TransientModel):
    _name = "purchase.exception.report"
    _description = "Purchase Exception Report"

    name = fields.Char("Name", default="Purchase Exception Report")
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses', required=True,
                                     help="Show the routes that apply on selected warehouses.")

    def generate_values(self, start_date, end_date, warehouse_ids):
        exception_orders = self.env['stock.picking']
        order_lines = {}

        if start_date and end_date and warehouse_ids:
            exception_orders = self.env['stock.picking'].search([
                ('scheduled_date', '>=', start_date),
                ('scheduled_date', '<=', end_date),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '=', 'done'),
                ('warehouse_id', 'in', warehouse_ids)
            ], order='scheduled_date asc')

            # print("exception_orders===================>",exception_orders)

            for rec in exception_orders:
                lines=rec.move_ids_without_package.filtered(lambda s: s.quantity_done > 0 and not s.quantity_done < s.product_uom_qty)
                # lines = rec.move_line_ids_without_package.filtered(lambda s: s.qty_done > 0)

                if lines:
                    # # Print information about the order
                    # print("Order ID:", rec.name)
                    # print("Order Date:", rec.date_order)

                    # Print information about each relevant order line
                    for line in lines:
                        vals = {'purchase_order': rec.group_id.name,
                                'product_code': line.product_id.default_code,
                                'product': line.product_id.name,
                                'product_qty': line.product_uom_qty,
                                'qty_received': line.quantity_done,
                                'order_case_type': line.product_packaging_id.name,
                                # 'rec_case_type': line.package_type_id.name,
                                }
                        # vals = {'purchase_order': rec.group_id.name,
                        #         'product_code': line.product_id.default_code,
                        #         'product': line.product_id.name,
                        #         'product_qty': line.reserved_qty,
                        #         'qty_received': line.qty_done,
                        #         'order_case_type': line.product_packaging_id.name,
                        #         'rec_case_type': line.package_type_id.name,
                        #         }

                    order_lines[line.id] = vals
            print("\torder_lines: ", order_lines)
        return order_lines

    def export_po_exception_report(self):
        action = self.env["ir.actions.actions"]._for_xml_id("so_and_po_lines.action_report_purchase_exception")
        action.update({
            'close_on_report_download': True
        })
        return action
