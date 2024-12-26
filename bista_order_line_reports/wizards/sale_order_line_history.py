from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrderLineHistory(models.TransientModel):
    _name = "sale.order.line.history"
    _description = "Sale Order Line History"

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses'
                                     , help="Show the routes that apply on selected warehouses.")

    def export_valuation_report(self):
        if self.env.context.get('for_view', False):
            warehouse_ids = tuple(self.warehouse_ids.ids)
            self.env.cr.execute('DELETE FROM sale_order_line_report')

            query = """
                INSERT INTO sale_order_line_report (
                    product_id, ordered_qty, delivered_qty, open_qty,
                    invoiced_qty, subtotal, unit_price,
                    open_order_value, shipping_status{warehouse_columns}
                )
                SELECT
                    sol.product_id AS product_id,
                    SUM(sol.product_uom_qty) AS ordered_qty,
                    SUM(sol.qty_delivered) AS delivered_qty,
                    SUM(sol.product_uom_qty) - SUM(sol.qty_delivered) AS open_qty,
                    SUM(sol.qty_invoiced) AS invoiced_qty,
                    SUM(sol.price_total) AS subtotal,
                    CASE
                        WHEN SUM(sol.product_uom_qty) = 0 THEN NULL
                        ELSE SUM(sol.price_total) / SUM(sol.product_uom_qty)
                    END AS unit_price,
                    CASE
                        WHEN SUM(sol.product_uom_qty) = 0 THEN NULL
                        ELSE (SUM(sol.price_total) / SUM(sol.product_uom_qty)) * (SUM(sol.product_uom_qty) - SUM(sol.qty_delivered))
                    END AS open_order_value,
                    CASE
                        WHEN SUM(sol.product_uom_qty) - SUM(sol.qty_delivered) = 0 THEN 'done'
                        ELSE 'open'
                    END AS shipping_status
                    {warehouse_values}
                FROM
                    sale_order_line sol
                LEFT JOIN
                    sale_order so ON sol.order_id = so.id
                WHERE
                    (sol.create_date AT TIME ZONE 'EST')::date >= %(start_date)s
                    AND (sol.create_date AT TIME ZONE 'EST')::date <= %(end_date)s
                    AND so.state NOT IN ('draft','sent','cancel') AND sol.product_uom_qty > 0
                    {warehouse_condition}
                GROUP BY
                    sol.product_id
                    {group_by_warehouse}
            """

            # Define placeholders for dynamic parts of the query
            warehouse_columns = ""
            warehouse_values = ""
            group_by_warehouse = ""
            warehouse_condition = ""

            # Check if warehouse_ids are provided
            if self.warehouse_ids:
                # Set up placeholders accordingly
                warehouse_columns = ", warehouse_id"
                warehouse_values = ", so.warehouse_id AS warehouse_id"
                warehouse_condition = "AND so.warehouse_id IN %(warehouse_ids)s"
                group_by_warehouse = ", so.warehouse_id"

            # Format the query with dynamic parts
            query = query.format(
                warehouse_columns=warehouse_columns,
                warehouse_values=warehouse_values,
                warehouse_condition=warehouse_condition,
                group_by_warehouse=group_by_warehouse
            )
            self.env.cr.execute(
                query,
                {
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'warehouse_ids': warehouse_ids if self.warehouse_ids else (),
                }
            )

            return {
                'name': 'Sale Order Line History Reports',
                'view_mode': 'tree,pivot',
                'view_type': 'tree',
                'res_model': 'sale.order.line.report',
                'view id': self.env.ref('bista_order_line_reports.sale_order_line_report_tree_view').id,
                'type': 'ir.actions.act_window',
            }
        # , self.env.ref('bista_order_line_reports.view_sale_order_line_report_search').id,
