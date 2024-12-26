from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrderLineHistory(models.TransientModel):
    _name = "purchase.order.line.history"
    _description = "Purchase Order Line History"

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses'
                                     , help="Show the routes that apply on selected warehouses.")

    def export_valuation_report(self):
        if self.env.context.get('for_view', False):
            warehouse_ids = tuple(self.warehouse_ids.ids)
            self.env.cr.execute('DELETE FROM purchase_order_line_report')

            query = """
                INSERT INTO purchase_order_line_report(
                        product_id, ordered_qty, delivered_qty,
                        open_qty, invoiced_qty, subtotal, unit_price,
                        open_order_value, shipping_status
                        {warehouse_columns})
                SELECT
                    pol.product_id AS product_id,
                    SUM(pol.product_qty) AS ordered_qty,
                    SUM(pol.qty_received) AS ordered_qty,
                    SUM(pol.product_qty) - SUM(pol.qty_received) AS open_qty,
                    SUM(pol.qty_invoiced) AS invoiced_qty,
                    SUM(pol.price_subtotal) AS subtotal,
                    CASE
                        WHEN SUM(pol.product_qty) = 0 THEN NULL
                        ELSE SUM(pol.price_subtotal) / SUM(pol.product_qty)
                    END AS unit_price,
                    CASE
                        WHEN SUM(pol.product_qty) = 0 THEN NULL
                        ELSE (SUM(pol.price_subtotal) / SUM(pol.product_qty)) * (SUM(pol.product_qty) - SUM(pol.qty_received))
                    END AS open_order_value,
                    CASE
                        WHEN SUM(pol.product_qty) - SUM(pol.qty_received) = 0 THEN 'done'
                        ELSE 'open'
                    END AS shipping_status
                    {warehouse_values}
                FROM
                    purchase_order_line pol
                LEFT JOIN
                    purchase_order po ON pol.order_id = po.id
                LEFT JOIN
                    stock_picking_type spt ON po.picking_type_id = spt.id
                LEFT JOIN
                    stock_warehouse sw ON spt.warehouse_id = sw.id
                WHERE
                    (pol.create_date AT TIME ZONE 'EST')::date >= %(start_date)s
                    AND (pol.create_date AT TIME ZONE 'EST')::date <= %(end_date)s
                    {warehouse_condition} AND po.state NOT IN ('draft','sent','cancel') 
                    AND pol.product_qty >0
                GROUP BY
                    pol.product_id
                    {group_by_warehouse}
            """
            #
            # Define placeholders for dynamic parts of the query
            warehouse_columns = ""
            warehouse_values = ""
            group_by_warehouse = ""
            warehouse_condition = ""

            # # Check if warehouse_ids are provided
            if self.warehouse_ids:
                # Set up placeholders accordingly
                warehouse_columns = ", warehouse_id"
                warehouse_values = ", sw.id AS warehouse_id"
                warehouse_condition = "AND sw.id IN %(warehouse_ids)s"
                group_by_warehouse = ", sw.id"

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
                'name': 'Purchase Order Line History Reports',
                'view_mode': 'tree,pivot',
                'view_type': 'tree',
                'res_model': 'purchase.order.line.report',
                'view id': self.env.ref('bista_order_line_reports.purchase_order_line_report_tree_view').id,
                'type': 'ir.actions.act_window',
            }
