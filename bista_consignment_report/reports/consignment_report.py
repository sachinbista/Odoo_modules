# -*- encoding: utf-8 -*-

from odoo import api, fields, models, tools


class ConsignmentReport(models.Model):
    _name = "consignment.report"
    _description = "ConsignmentAnalysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    name = fields.Char('Order Reference', readonly=True)
    date = fields.Datetime('Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
    qty_to_received = fields.Float('Purchase Qty', readonly=True)
    qty_delivered = fields.Float('Sale Qty', readonly=True)
    owner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order #', readonly=True)
    order_id = fields.Many2one('sale.order', 'Sale Order #', readonly=True)

    def _with_consignment(self):
        return ""

    def _select_consignment(self):

        select_ = f"""
                MIN(sml.id) AS id,
                sml.product_id AS product_id,
                sml.reference AS name,
                sml.date AS date,
                sml.owner_id AS owner_id,
                sm.company_id AS company_id,
                t.categ_id AS categ_id,
                CASE WHEN sm.purchase_line_id IS NOT NULL THEN
                sml.qty_done
                ELSE 0 END as qty_to_received,
                CASE WHEN sm.sale_line_id IS NOT NULL THEN
                sml.qty_done
                ELSE sml.qty_done END as qty_delivered,
                p.id AS purchase_order_id,
                pp.product_tmpl_id AS product_tmpl_id,
                s.id AS order_id"""
        additional_fields_info = self._select_additional_fields()
        template = """,
            %s AS %s"""
        for fname, query_info in additional_fields_info.items():
            select_ += template % (query_info, fname)
        return select_

    def _select_additional_fields(self):
        """Hook to return additional fields SQL specification for select part of the table query.

        :returns: mapping field -> SQL computation of field, will be converted to '_ AS _field' in the final table definition
        :rtype: dict
        """
        return {}

    def _from_consignment(self):
        return """
            stock_move_line sml
            JOIN stock_move sm ON sm.id=sml.move_id
            JOIN res_partner rp ON rp.id =sml.owner_id
            JOIN product_product pp ON sml.product_id=pp.id
            JOIN product_template t ON pp.product_tmpl_id=t.id
            LEFT JOIN sale_order_line sol on sol.id=sm.sale_line_id
            LEFT JOIN sale_order s on s.id=sol.order_id
            LEFT JOIN purchase_order_line pol on pol.id=sm.purchase_line_id
            LEFT JOIN purchase_order p on p.id=pol.order_id
            """

    def _where_consignment(self):
        return """
            sml.owner_id IS NOT NULL and sm.state in('done')"""

    def _group_by_consignment(self):
        return """
           sml.product_id,
           sml.reference,
           sml.date,
           sml.owner_id,
           sm.company_id,
           t.categ_id,
           sml.qty_done,
           sm.purchase_line_id,
           sm.sale_line_id,
           pp.product_tmpl_id,
           p.id,
           s.id
        """

    def _query(self):
        with_ = self._with_consignment()
        return f"""
            {"WITH" + with_ + "(" if with_ else ""}
            SELECT {self._select_consignment()}
            FROM {self._from_consignment()}
            WHERE {self._where_consignment()}
            GROUP BY {self._group_by_consignment()}
            {")" if with_ else ""}
        """

    @property
    def _table_query(self):
        return self._query()



