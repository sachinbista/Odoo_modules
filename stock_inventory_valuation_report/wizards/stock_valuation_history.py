from odoo import api, fields, models, _
import xlwt
from io import BytesIO
import xlsxwriter, base64
from datetime import datetime
from odoo.exceptions import ValidationError,UserError
import logging
_logger = logging.getLogger(__name__)

class ViewReport(models.TransientModel):
    _name = "view.report"
    _description = "View Report"

    file = fields.Binary('File',readonly=True)
    file_name = fields.Char('File Name',readonly=True)


class StockValuationHistory(models.TransientModel):
    _name = "stock.valuation.history"
    _description = "Stock Valuation History"

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses', required=True,help="Show the routes that apply on selected warehouses.")
    report_data = fields.Binary('Report')
    location_ids = fields.Many2many('stock.location', 'Location')
    filter_by = fields.Selection([('product', "Product"), ('category', "Category")],string="Filter By", default='product')
    included_product_category_ids = fields.Many2many('product.category', 'in_siv_pro_categ_rel', 'in_siv_id', 'in_pro_categ_id', string='Include Categories')
    excluded_product_category_ids = fields.Many2many('product.category', 'ex_siv_pro_categ_rel', 'ex_siv_id', 'ex_pro_categ_id', string='Exclude Categories')

    type_product_ids = fields.Many2many('type.product', string='Type')

    @api.onchange('included_product_category_ids')
    def onchange_included_product_category_ids(self):
        if self.included_product_category_ids:
            self.excluded_product_category_ids = False

    @api.onchange('excluded_product_category_ids')
    def onchange_excluded_product_category_ids(self):
        if self.excluded_product_category_ids:
            self.included_product_category_ids = False

    def export_valuation_report(self):
        self.env['res.config.settings'].sudo().create({'module_stock_landed_costs': True}).execute()
        warehouse_ids = self.warehouse_ids.ids
        location_id = self.warehouse_ids.view_location_id.ids
        locations = self.env['stock.location'].search([('id', 'child_of', location_id)])
        location_ids = locations.ids
        internal_location_ids = locations.filtered(lambda x: x.usage == 'internal').ids
        inventory_loc_ids = self.env['stock.location'].search([
        ('usage', '=', 'inventory'),
        ('active', '=', True)])

        type_product = self.type_product_ids.mapped('type_product')

        if self.included_product_category_ids:
            for included_product_category_id in self.included_product_category_ids:
                category = included_product_category_id
                while category.parent_id:
                    self.included_product_category_ids = [(4, category.parent_id.id)]
                    category = category.parent_id

        if self.env.context.get('for_view', False):
            self.env.cr.execute('DELETE FROM stock_valuation_report')
            query = """ 
                    insert into stock_valuation_report (product_id,on_hand,starting_quantity,starting_value,ending_quantity,ending_value,open_po,open_so,reserved_qty,quantity_received,value_received,
                    quantity_shipped,valued_shipped,inv_adjustment_qty,landed_cost_per_item,position,available_qty)
                    select product_id,sum(on_hand_qty) as on_hand_qty,sum(starting_quantity) as starting_quantity,sum(starting_value) as starting_value,
                    sum(ending_quantity) as ending_quantity,sum(ending_value) as ending_value, sum(open_purchase_order_count) as open_purchase_order_count,
                    sum(open_sale_order_count) as open_sale_order_count,
                    sum(reserved) as reserved,
                    sum(incoming_qty) as incoming_qty,
                    sum(incoming_value) as incoming_value,
                    sum(-outgoing_qty) as outgoing_qty,
                    sum(-outgoing_value) as outgoing_value,
                    sum(quantity_done) AS quantity_done,
                    sum(avg_landed_cost) as avg_landed_cost,
                    (sum(on_hand_qty)+sum(open_purchase_order_count)) as position,
                    ((sum(on_hand_qty)+sum(open_purchase_order_count)) - sum(open_sale_order_count) - sum(reserved)) as available_qty from (select 
                    sm.product_id,
                    0 AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    0 AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    0 AS quantity_done,
                    0 as avg_landed_cost
                    from stock_move sm
                    LEFT JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                    LEFT JOIN
                        product_product pp ON sm.product_id = pp.id
                    LEFT JOIN
                        product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE
                    sm.state = 'done'
                    AND (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    AND  sm.location_dest_id in %(location_ids)s or sm.location_id in %(location_ids)s
                    GROUP BY sm.product_id
    UNION ALL


    SELECT          svl.product_id,
                    0 AS on_hand_qty,
                    SUM(CASE WHEN
                        (svl.create_date at time zone 'EST')::date < %(start_date)s
                        THEN svl.quantity ELSE 0 END) AS starting_quantity,
                    SUM(CASE WHEN
                        (svl.create_date at time zone 'EST')::date < %(start_date)s
                        THEN svl.value ELSE 0 END) AS starting_value,
                    SUM(CASE WHEN
                        (svl.create_date at time zone 'EST')::date <= %(end_date)s
                        THEN svl.quantity ELSE 0 END) AS ending_quantity,
                    SUM(CASE WHEN
                        (svl.create_date at time zone 'EST')::date <= %(end_date)s
                        THEN svl.value ELSE 0 END) AS ending_value,
                    COALESCE(0) AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    0 AS quantity_done,
                    0 as avg_landed_cost
                    FROM stock_valuation_layer svl
                    INNER JOIN product_product pp ON pp.id = svl.product_id
                    INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id

                    WHERE
                    pt.type = 'product'
                    AND  svl.warehouse_id in %(warehouse_ids)s
                    AND (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    GROUP BY svl.product_id
    UNION ALL

    select 
                    sq.product_id,
                    sum(sq.quantity) AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    COALESCE(0) AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    0 AS quantity_done,
                    0 as avg_landed_cost
                    from stock_quant sq
                    where sq.location_id in %(internal_location_ids)s
                    GROUP BY sq.product_id 
                   
    UNION ALL

                    SELECT 
                        p.id,
                        0 AS on_hand_qty,
                        0 AS starting_quantity,
                        0 AS starting_value,
                        0 AS ending_quantity,
                        0 AS ending_value,
                        COALESCE(SUM(pol.product_qty - pol.qty_received), 0) AS open_purchase_order_count,
                        0 AS open_sale_order_count,
                        0 AS reserved,
                        0 AS incoming_qty,
                        0 AS incoming_value,
                        0 AS outgoing_qty,
                        0 AS outgoing_value,
                        0 AS quantity_done,
                        0 as avg_landed_cost
                    FROM 
                        purchase_order AS po
                    left join 
                        stock_picking_type as spt on po.picking_type_id = spt.id
                    JOIN 
                        purchase_order_line AS pol ON po.id = pol.order_id AND pol.product_qty != pol.qty_received
                    JOIN 
                        product_product AS p ON pol.product_id = p.id
                    WHERE 
                        po.state in ('purchase', 'done')
                        AND spt.warehouse_id in %(warehouse_ids)s
                    GROUP BY p.id

    UNION ALL

                SELECT 
                        sol.product_id,
                        0 AS on_hand_qty,
                        0 AS starting_quantity,
                        0 AS starting_value,
                        0 AS ending_quantity,
                        0 AS ending_value,
                        0 AS open_purchase_order_count,
                        COALESCE(SUM(CASE WHEN sml.reserved_uom_qty is not null THEN ((sol.product_uom_qty - sol.qty_delivered) - sml.reserved_uom_qty) ELSE sol.product_uom_qty END), 0) AS open_sale_order_count,
                        COALESCE(SUM(sml.reserved_uom_qty), 0) AS reserved,
                        0 AS incoming_qty,
                        0 AS incoming_value,
                        0 AS outgoing_qty,
                        0 AS outgoing_value,
                        0 AS quantity_done,
                        0 as avg_landed_cost
                    FROM 
                        sale_order AS so
                    JOIN 
                        sale_order_line AS sol ON so.id = sol.order_id AND sol.product_uom_qty != sol.qty_delivered
                    left join 
                        stock_move AS sm ON sm.sale_line_id = sol.id and sm.state in ('assigned', 'confirmed')
                    left join 
                        stock_move_line AS sml ON sml.move_id = sm.id and sml.state in ('assigned', 'partially_available')
                    JOIN 
                        product_product AS p ON sol.product_id = p.id
                    WHERE 
                        so.state not in ('cancel', 'sent', 'draft')
                        AND so.warehouse_id in %(warehouse_ids)s
                    GROUP BY sol.product_id
    UNION ALL

                    SELECT 
                    sm.product_id,
                    0 AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    0 AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    SUM(CASE WHEN sm.location_dest_id in %(location_ids)s AND
                        (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                        (svl.create_date at time zone 'EST')::date <= %(end_date)s
                        THEN svl.quantity ELSE 0 END) AS incoming_qty,
                    SUM(CASE WHEN sm.location_dest_id in %(location_ids)s AND
                        (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                        (svl.create_date at time zone 'EST')::date <= %(end_date)s
                        THEN svl.value ELSE 0 END) AS incoming_value,
                    SUM(CASE WHEN sm.location_id in %(location_ids)s AND
                        (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                        (svl.create_date at time zone 'EST')::date <= %(end_date)s
                        THEN svl.quantity ELSE 0 END) AS outgoing_qty,
                    SUM(CASE WHEN sm.location_id in %(location_ids)s AND
                        (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                        (svl.create_date at time zone 'EST')::date <= %(end_date)s
                        THEN svl.value ELSE 0 END) AS outgoing_value,
                    0 AS quantity_done,
                    0 as avg_landed_cost
                    from stock_move sm
                    LEFT JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                    WHERE
                    sm.state = 'done'
                    AND  (sm.location_dest_id in %(location_ids)s or sm.location_id in %(location_ids)s)
                    GROUP BY sm.product_id


    UNION ALL
                    select product_id,
                    0 AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    0 AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    sum(quantity_done) AS quantity_done,
                    0 as avg_landed_cost from (

                    select product_id,sum(quantity_done) AS quantity_done from stock_move where state='done' and location_id in %(inventory_loc_ids)s 
                    and location_dest_id in %(location_ids)s and (date at time zone 'EST')::date >= %(start_date)s and (date at time zone 'EST')::date <= %(end_date)s
                    GROUP BY product_id

                    UNION ALL

                    select product_id,-sum(quantity_done) AS quantity_done from stock_move where state='done' and location_id in %(location_ids)s 
                    and location_dest_id in %(inventory_loc_ids)s and (date at time zone 'EST')::date >= %(start_date)s and (date at time zone 'EST')::date <= %(end_date)s GROUP BY product_id
                    ) as inv GROUP by product_id

    UNION ALL

                    SELECT 
                    sval.product_id,
                    0 AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    0 AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    0 AS quantity_done,
                    SUM(sval.quantity/sval.additional_landed_cost) / COUNT(DISTINCT sval.cost_id) as avg_landed_cost
                    FROM 
                        purchase_order_line AS pol
                    LEFT JOIN 
                        purchase_order AS po ON pol.order_id = po.id
                    LEFT JOIN
                        stock_picking_type as spt on po.picking_type_id = spt.id
                    LEFT JOIN
                        purchase_order_stock_picking_rel AS posp ON posp.purchase_order_id = po.id
                    LEFT JOIN
                        stock_landed_cost_stock_picking_rel As slsp ON slsp.stock_picking_id = posp.stock_picking_id
                    LEFT JOIN 
                        stock_landed_cost AS lc ON lc.id = slsp.stock_landed_cost_id
                    left join 
                        stock_valuation_adjustment_lines as sval on sval.cost_id = lc.id
                    WHERE 
                    spt.warehouse_id in %(warehouse_ids)s
                    AND (sval.create_date at time zone 'EST')::date >= %(start_date)s
                    AND (sval.create_date at time zone 'EST')::date <= %(end_date)s
                    AND sval.product_id = pol.product_id
                    AND lc.state='done'
                    GROUP BY sval.product_id

                    ) as result group by product_id;"""

        xls_file_name = 'stock_inventory_valuation_report.xlsx'
        workbook = xlsxwriter.Workbook('/tmp/' + xls_file_name)
        inventory_valuation_report_sheet = workbook.add_worksheet('Stock Inventory Valuation Report')
        valuation_header = ['Item Number', 'Item Description', 'Item Type', 'UPC Code', 'GTIN', 'On Hand', 'Open PO',
                          'Position', 'Open SO', 'Reserved', 'Available', 'Landed Cost Per Item','Starting Quantity',
                          'Quantity Received', 'Quantity Shipped', 'Adjustment', 'Ending Quantity', 'Starting Value',
                          'Value Received', 'Valued Shipped', 'Ending Value']
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'align': 'left','border':1,'border_color':'#000000','text_wrap':'vjustify'})
        heading_part_1 = workbook.add_format({'border':1, 'align':'left', 'bold': True,'border_color':'#000000','text_wrap':'vjustify'})
        value_part_1 = workbook.add_format({'border':1, 'align':'left', 'border_color':'#000000','text_wrap':'vjustify'})
        inventory_valuation_report_sheet.set_row(0, 20)
        inventory_valuation_report_sheet.set_column(0, 0, 50)
        inventory_valuation_report_sheet.set_row(2, 20)
        inventory_valuation_report_sheet.set_column(1, 2, 20)
        inventory_valuation_report_sheet.set_column(2, 22, 25)
        warehouse_names = ', '.join(self.warehouse_ids.mapped('name'))
        inventory_valuation_report_sheet.write(1, 0, 'Based on Date Range', heading_part_1)
        inventory_valuation_report_sheet.set_row(1, 20)
        inventory_valuation_report_sheet.write(1, 1, self.start_date.strftime("%x") +' To '+ self.end_date.strftime("%x"), date_format)
        inventory_valuation_report_sheet.write(2, 0, 'Selectd Warehouses', heading_part_1)
        inventory_valuation_report_sheet.write(2, 1, warehouse_names, value_part_1)
        inventory_valuation_report_sheet.set_row(2, 20)
        inventory_valuation_report_sheet.set_column(2, 1, 20)
        inventory_valuation_report_sheet.write(3, 0, 'Item Types', heading_part_1)
        inventory_valuation_report_sheet.write(3, 1, 'Product', value_part_1)
        inventory_valuation_report_sheet.set_row(3, 20)

        # total_aging_report_sheet.freeze_panes(1,0)

        all_text = workbook.add_format({'border':1,'border_color':'#000000','text_wrap':'vjustify'})
        all_headers = workbook.add_format({'border':1, 'align':'left', 'bold': True,'border_color':'#000000', 'bg_color': '#8e918f', 'text_wrap':'vjustify'})
        grandparent_bg_color = workbook.add_format({'bg_color':'#B9D86C','border':1,'border_color':'#6698DE','text_wrap':'vjustify'})
        row_bg_color = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFFFF','border':1,'border_color':'#000000','text_wrap':'vjustify'})
        total_bg_color = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFFFF', 'bold': True, 'border':1,'border_color':'#000000','text_wrap':'vjustify'})
        row_bg_color_negative = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#FFCCCB','border':1,'border_color':'#000000','text_wrap':'vjustify'})
        row_bg_color_total = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#8e918f','border':1,'border_color':'#000000','text_wrap':'vjustify'})
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy', 'align': 'left','border':1,'border_color':'#6698DE','text_wrap':'vjustify'})
        currency_symbol = workbook.add_format({'num_format': '$#,##0.00', 'align': 'right','border':1,'border_color':'#6698DE'})
        currency_symbol_parent = workbook.add_format({'bg_color':'#FFFFFF',
                                                        'num_format': '$#,##0.00',
                                                        'align': 'right','border':1,'border_color':'#000000'})
        currency_symbol_parent_negative = workbook.add_format({'bg_color':'#FFCCCB',
                                                        'num_format': '$#,##0.00',
                                                        'align': 'right','border':1,'border_color':'#000000'})
        currency_symbol_grandparent = workbook.add_format({'bg_color':'#B9D86C',
                                                        'num_format': '$#,##0.00',
                                                        'align': 'right','border':1,'border_color':'#6698DE'})
        grand_total_bg_color = workbook.add_format({'bg_color': '#C79DE9','border':1,'border_color':'#6698DE'})
        currency_symbol_grand_total = workbook.add_format({'bg_color': '#8e918f',
                                                        'num_format': '$#,##0.00',
                                                        'align': 'right','border':1,'border_color':'#000000'})
        currency_symbol_grand_total_negative = workbook.add_format({'bg_color':'#FFCCCB',
                                                        'num_format': '$#,##0.00',
                                                        'align': 'right','border':1,'border_color':'#000000'})

        row = 5
        col = 0
        for header_column in valuation_header:
             inventory_valuation_report_sheet.write(row, col, header_column, all_headers)
             inventory_valuation_report_sheet.set_row(row, 30)
             col += 1
        if self.env.context.get('for_excel', False):
            query = """select product_id,sum(on_hand_qty) as on_hand_qty,sum(starting_quantity) as starting_quantity,sum(starting_value) as starting_value,
                sum(ending_quantity) as ending_quantity,sum(ending_value) as ending_value, sum(open_purchase_order_count) as open_purchase_order_count,
                sum(open_sale_order_count) as open_sale_order_count,
                sum(reserved) as reserved,
                sum(incoming_qty) as incoming_qty,
                sum(incoming_value) as incoming_value,
                sum(outgoing_qty) as outgoing_qty,
                sum(outgoing_value) as outgoing_value,
                sum(quantity_done) AS quantity_done,
                sum(avg_landed_cost) as avg_landed_cost,
                (sum(on_hand_qty)+sum(open_purchase_order_count)) as position,
                ((sum(on_hand_qty)+sum(open_purchase_order_count)) - sum(open_sale_order_count) - sum(reserved)) as available_qty from (select 
                sm.product_id,
                0 AS on_hand_qty,
                0 AS starting_quantity,
                0 AS starting_value,
                0 AS ending_quantity,
                0 AS ending_value,
                0 AS open_purchase_order_count,
                0 AS open_sale_order_count,
                0 AS reserved,
                0 AS incoming_qty,
                0 AS incoming_value,
                0 AS outgoing_qty,
                0 AS outgoing_value,
                0 AS quantity_done,
                0 as avg_landed_cost
                from stock_move sm
                LEFT JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                LEFT JOIN
                    product_product pp ON sm.product_id = pp.id
                LEFT JOIN
                    product_template pt ON pt.id = pp.product_tmpl_id
                WHERE
                sm.state = 'done'
                AND (svl.create_date at time zone 'EST')::date <= %(end_date)s
                AND  sm.location_dest_id in %(location_ids)s or sm.location_id in %(location_ids)s
                GROUP BY sm.product_id
UNION ALL


SELECT          svl.product_id,
                0 AS on_hand_qty,
                SUM(CASE WHEN
                    (svl.create_date at time zone 'EST')::date < %(start_date)s
                    THEN svl.quantity ELSE 0 END) AS starting_quantity,
                SUM(CASE WHEN
                    (svl.create_date at time zone 'EST')::date < %(start_date)s
                    THEN svl.value ELSE 0 END) AS starting_value,
                SUM(CASE WHEN
                    (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    THEN svl.quantity ELSE 0 END) AS ending_quantity,
                SUM(CASE WHEN
                    (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    THEN svl.value ELSE 0 END) AS ending_value,
                COALESCE(0) AS open_purchase_order_count,
                0 AS open_sale_order_count,
                0 AS reserved,
                0 AS incoming_qty,
                0 AS incoming_value,
                0 AS outgoing_qty,
                0 AS outgoing_value,
                0 AS quantity_done,
                0 as avg_landed_cost
                FROM stock_valuation_layer svl
                INNER JOIN product_product pp ON pp.id = svl.product_id
                INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id

                WHERE
                pt.type = 'product'
                AND  svl.warehouse_id in %(warehouse_ids)s
                AND (svl.create_date at time zone 'EST')::date <= %(end_date)s
                GROUP BY svl.product_id
UNION ALL

select 
                sq.product_id,
                sum(sq.quantity) AS on_hand_qty,
                0 AS starting_quantity,
                0 AS starting_value,
                0 AS ending_quantity,
                0 AS ending_value,
                COALESCE(0) AS open_purchase_order_count,
                0 AS open_sale_order_count,
                0 AS reserved,
                0 AS incoming_qty,
                0 AS incoming_value,
                0 AS outgoing_qty,
                0 AS outgoing_value,
                0 AS quantity_done,
                0 as avg_landed_cost
                from stock_quant sq
                where sq.location_id in %(internal_location_ids)s
                GROUP BY sq.product_id

UNION ALL

                SELECT 
                    p.id,
                    0 AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    COALESCE(SUM(pol.product_qty - pol.qty_received), 0) AS open_purchase_order_count,
                    0 AS open_sale_order_count,
                    0 AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    0 AS quantity_done,
                    0 as avg_landed_cost
                FROM 
                    purchase_order AS po
                left join 
                    stock_picking_type as spt on po.picking_type_id = spt.id
                JOIN 
                    purchase_order_line AS pol ON po.id = pol.order_id AND pol.product_qty != pol.qty_received
                JOIN 
                    product_product AS p ON pol.product_id = p.id
                WHERE 
                    po.state in ('purchase', 'done')
                    AND spt.warehouse_id in %(warehouse_ids)s
                GROUP BY p.id

UNION ALL

            SELECT 
                    sol.product_id,
                    0 AS on_hand_qty,
                    0 AS starting_quantity,
                    0 AS starting_value,
                    0 AS ending_quantity,
                    0 AS ending_value,
                    0 AS open_purchase_order_count,
                    COALESCE(SUM(CASE WHEN sml.reserved_uom_qty is not null THEN ((sol.product_uom_qty - sol.qty_delivered) - sml.reserved_uom_qty) ELSE sol.product_uom_qty END), 0) AS open_sale_order_count,
                    COALESCE(SUM(sml.reserved_uom_qty), 0) AS reserved,
                    0 AS incoming_qty,
                    0 AS incoming_value,
                    0 AS outgoing_qty,
                    0 AS outgoing_value,
                    0 AS quantity_done,
                    0 as avg_landed_cost
                FROM 
                    sale_order AS so
                JOIN 
                    sale_order_line AS sol ON so.id = sol.order_id AND sol.product_uom_qty != sol.qty_delivered
                left join 
                    stock_move AS sm ON sm.sale_line_id = sol.id and sm.state in ('assigned', 'confirmed')
                left join 
                    stock_move_line AS sml ON sml.move_id = sm.id and sml.state in ('assigned', 'partially_available')
                JOIN 
                    product_product AS p ON sol.product_id = p.id
                WHERE 
                    so.state not in ('cancel', 'sent', 'draft')
                    AND so.warehouse_id in %(warehouse_ids)s
                GROUP BY sol.product_id
UNION ALL

                SELECT 
                sm.product_id,
                0 AS on_hand_qty,
                0 AS starting_quantity,
                0 AS starting_value,
                0 AS ending_quantity,
                0 AS ending_value,
                0 AS open_purchase_order_count,
                0 AS open_sale_order_count,
                0 AS reserved,
                SUM(CASE WHEN sm.location_dest_id in %(location_ids)s AND
                    (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                    (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    THEN svl.quantity ELSE 0 END) AS incoming_qty,
                SUM(CASE WHEN sm.location_dest_id in %(location_ids)s AND
                    (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                    (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    THEN svl.value ELSE 0 END) AS incoming_value,
                SUM(CASE WHEN sm.location_id in %(location_ids)s AND
                    (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                    (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    THEN svl.quantity ELSE 0 END) AS outgoing_qty,
                SUM(CASE WHEN sm.location_id in %(location_ids)s AND
                    (svl.create_date at time zone 'EST')::date >= %(start_date)s AND 
                    (svl.create_date at time zone 'EST')::date <= %(end_date)s
                    THEN svl.value ELSE 0 END) AS outgoing_value,
                0 AS quantity_done,
                0 as avg_landed_cost
                from stock_move sm
                LEFT JOIN stock_valuation_layer AS svl ON svl.stock_move_id = sm.id
                WHERE
                sm.state = 'done'
                AND  (sm.location_dest_id in %(location_ids)s or sm.location_id in %(location_ids)s)
                GROUP BY sm.product_id


UNION ALL
                select product_id,
                0 AS on_hand_qty,
                0 AS starting_quantity,
                0 AS starting_value,
                0 AS ending_quantity,
                0 AS ending_value,
                0 AS open_purchase_order_count,
                0 AS open_sale_order_count,
                0 AS reserved,
                0 AS incoming_qty,
                0 AS incoming_value,
                0 AS outgoing_qty,
                0 AS outgoing_value,
                sum(quantity_done) AS quantity_done,
                0 as avg_landed_cost from (

                select product_id,sum(quantity_done) AS quantity_done from stock_move where state='done' and location_id in %(inventory_loc_ids)s 
                and location_dest_id in %(location_ids)s and (date at time zone 'EST')::date >= %(start_date)s and (date at time zone 'EST')::date <= %(end_date)s
                GROUP BY product_id

                UNION ALL

                select product_id,-sum(quantity_done) AS quantity_done from stock_move where state='done' and location_id in %(location_ids)s 
                and location_dest_id in %(inventory_loc_ids)s and (date at time zone 'EST')::date >= %(start_date)s and (date at time zone 'EST')::date <= %(end_date)s GROUP BY product_id
                ) as inv GROUP by product_id

UNION ALL

                SELECT 
                sval.product_id,
                0 AS on_hand_qty,
                0 AS starting_quantity,
                0 AS starting_value,
                0 AS ending_quantity,
                0 AS ending_value,
                0 AS open_purchase_order_count,
                0 AS open_sale_order_count,
                0 AS reserved,
                0 AS incoming_qty,
                0 AS incoming_value,
                0 AS outgoing_qty,
                0 AS outgoing_value,
                0 AS quantity_done,
                SUM(sval.quantity/sval.additional_landed_cost) / COUNT(DISTINCT sval.cost_id) as avg_landed_cost
                FROM 
                    purchase_order_line AS pol
                LEFT JOIN 
                    purchase_order AS po ON pol.order_id = po.id
                LEFT JOIN
                    stock_picking_type as spt on po.picking_type_id = spt.id
                LEFT JOIN
                    purchase_order_stock_picking_rel AS posp ON posp.purchase_order_id = po.id
                LEFT JOIN
                    stock_landed_cost_stock_picking_rel As slsp ON slsp.stock_picking_id = posp.stock_picking_id
                LEFT JOIN 
                    stock_landed_cost AS lc ON lc.id = slsp.stock_landed_cost_id
                left join 
                    stock_valuation_adjustment_lines as sval on sval.cost_id = lc.id

                WHERE 
                spt.warehouse_id in %(warehouse_ids)s
                AND (sval.create_date at time zone 'EST')::date >= %(start_date)s
                AND (sval.create_date at time zone 'EST')::date <= %(end_date)s
                AND sval.product_id = pol.product_id
                AND lc.state='done'
                GROUP BY sval.product_id

                ) as result group by product_id;"""
        self.env.cr.execute(query, {'start_date': self.start_date, 'end_date': self.end_date,
            'inventory_loc_ids': tuple(inventory_loc_ids.ids),
            'warehouse_ids': tuple(warehouse_ids), 'location_ids': tuple(location_ids), 'internal_location_ids': tuple(internal_location_ids)})
        if self.env.context.get('for_view', False):
            return {
                'name': 'Stock Valuation Reports (From:' + str(self.start_date) + ' - To:' + str(self.end_date) + ')',
                'view_mode': 'tree',
                'view_type': 'tree',
                'res_model': 'stock.valuation.report',
                'view id': self.env.ref('stock_inventory_valuation_report.stock_valuation_history_tree_view').id,
                'type': 'ir.actions.act_window',
                'domain': [('product_id.type_product', 'in', type_product)],
            }
                

        inventory_data = self.env.cr.dictfetchall()
        if self.env.context.get('for_excel', False):
            row += 1
            col = 0
            tmp = 0
            product_obj = self.env['product.product']
            for data in inventory_data:
                if self.included_product_category_ids:
                    product_id = product_obj.search([('id', '=', data['product_id']),('categ_id', 'in', self.included_product_category_ids.ids)])
                elif self.excluded_product_category_ids:
                    product_id = product_obj.search([('id', '=', data['product_id']),('categ_id', 'not in', self.excluded_product_category_ids.ids)])
                elif not self.included_product_category_ids and not self.excluded_product_category_ids:
                    product_id = product_obj.search([('id', '=', data['product_id'])])
                if product_id:
                    inventory_valuation_report_sheet.write(row, col, product_id.name or None, row_bg_color)
                    inventory_valuation_report_sheet.write(row, col+1, product_id.default_code or None, row_bg_color)
                    inventory_valuation_report_sheet.write(row, col+2, product_id.detailed_type or None, row_bg_color)
                    inventory_valuation_report_sheet.write(row, col+3, product_id.barcode or None, row_bg_color)
                    inventory_valuation_report_sheet.write(row, col+4, None, row_bg_color)
                    inventory_valuation_report_sheet.write(row, col+5, data['on_hand_qty'], row_bg_color if data['on_hand_qty'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+6, data['open_purchase_order_count'], row_bg_color if data['open_purchase_order_count'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+7, data['position'], row_bg_color if data['position'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+8, data['open_sale_order_count'], row_bg_color if data['open_sale_order_count'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+9, data['reserved'], row_bg_color if data['reserved'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+10, data['available_qty'], row_bg_color if data['available_qty'] >= 0 else row_bg_color_negative) 
                    inventory_valuation_report_sheet.write(row, col+11, data['avg_landed_cost'], row_bg_color if data['avg_landed_cost'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+12, data['starting_quantity'], row_bg_color if data['starting_quantity'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+13, data['incoming_qty'], row_bg_color if data['incoming_qty'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+14, -data['outgoing_qty'] if data['outgoing_qty'] < 0 else data['outgoing_qty'], row_bg_color if -data['outgoing_qty'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+15, data['quantity_done'], row_bg_color if data['quantity_done'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+16, data['ending_quantity'], row_bg_color if data['ending_quantity'] >= 0 else row_bg_color_negative)
                    inventory_valuation_report_sheet.write(row, col+17, data['starting_value'], currency_symbol_parent if data['starting_value'] >= 0 else currency_symbol_parent_negative)
                    inventory_valuation_report_sheet.write(row, col+18, data['incoming_value'], currency_symbol_parent if data['incoming_value'] >= 0 else currency_symbol_parent_negative)
                    inventory_valuation_report_sheet.write(row, col+19, -data['outgoing_value'], currency_symbol_parent if -data['outgoing_value'] >= 0 else currency_symbol_parent_negative)
                    inventory_valuation_report_sheet.write(row, col+20, data['ending_value'], currency_symbol_parent if data['ending_value'] >= 0 else currency_symbol_parent_negative)
                    row += 1
                    tmp += 1
                    if tmp == len(inventory_data):
                        inventory_valuation_report_sheet.write(row, col+4, "Total", total_bg_color)
                        inventory_valuation_report_sheet.write(row, col+5, sum([data['on_hand_qty'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['on_hand_qty'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+6, sum([data['open_purchase_order_count'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['open_purchase_order_count'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+7, sum([data['position'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['position'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+8, sum([data['open_sale_order_count'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['open_sale_order_count'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+9, sum([data['reserved'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['reserved'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+10, sum([data['available_qty'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['available_qty'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+11, sum([data['avg_landed_cost'] for data in inventory_data]),
                                                                            currency_symbol_grand_total if sum([data['avg_landed_cost'] for data in inventory_data]) >= 0 else currency_symbol_grand_total_negative)
                        inventory_valuation_report_sheet.write(row, col+12, sum([data['starting_quantity'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['starting_quantity'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+13, sum([data['incoming_qty'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['incoming_qty'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+14, sum([data['outgoing_qty'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['outgoing_qty'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+15, sum([data['quantity_done'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['quantity_done'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+16, sum([data['ending_quantity'] for data in inventory_data]),
                                                                            row_bg_color_total if sum([data['ending_quantity'] for data in inventory_data]) >= 0 else row_bg_color_negative)
                        inventory_valuation_report_sheet.write(row, col+17, sum([data['starting_value'] for data in inventory_data]),
                                                                            currency_symbol_grand_total if sum([data['starting_value'] for data in inventory_data]) >= 0 else currency_symbol_grand_total_negative)
                        inventory_valuation_report_sheet.write(row, col+18, sum([data['incoming_value'] for data in inventory_data]),
                                                                            currency_symbol_grand_total if sum([data['incoming_value'] for data in inventory_data]) >= 0 else currency_symbol_grand_total_negative)
                        inventory_valuation_report_sheet.write(row, col+19, sum([data['outgoing_value'] for data in inventory_data]),
                                                                            currency_symbol_grand_total if sum([data['outgoing_value'] for data in inventory_data]) >= 0 else currency_symbol_grand_total_negative)
                        inventory_valuation_report_sheet.write(row, col+20, sum([data['ending_value'] for data in inventory_data]),
                                                                        currency_symbol_grand_total if sum([data['ending_value'] for data in inventory_data]) >= 0 else currency_symbol_grand_total_negative)
            workbook.close()
            file_data = base64.b64encode(open('/tmp/' +
                                                   xls_file_name, 'rb').read())
            if file_data:
                self.write({'report_data': file_data})
            filename = 'stock_valuation_report'
            return {
                'name': 'Stock Valuation Report',
                'type': 'ir.actions.act_url',
                'url': "web/content/?model=stock.valuation.history&id=" +
                    str(self.id) +\
                    "&filename_field=filename&field=report_data&download=true\
                    &filename=" + filename,
                'target': 'self',
            }