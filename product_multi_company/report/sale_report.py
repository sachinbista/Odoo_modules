from odoo import models, fields

class SaleReport(models.Model):
    _inherit = 'sale.report'

    status = fields.Selection([
        ('active', 'Active'), ('discontinued', 'Discontinued')],
        string='Product Status', readonly=True)
    barcode = fields.Char(string='UPC', readonly=True)
    default_code = fields.Char(string='SKU', readonly=True)
    product_sub_categ_1 = fields.Many2one('product.category', string='Product Sub-Category 1', readonly=True)
    product_sub_categ_2 = fields.Many2one('product.category', string='Product Sub-Category 2', readonly=True)
    is_gift = fields.Boolean(string='Gift With Purchase / Not for Individual Sale', readonly=True)
    product_group_id = fields.Many2one('product.group', string='Product Group', readonly=True)
    release_id = fields.Many2one('product.release', string='Release', readonly=True)
    collection_id = fields.Many2one('product.collection', string='Collection / Season / Range', readonly=True)
    production_edition = fields.Selection([('core', 'Core'), ('limited', 'Limited Edition')],
                                          string='Core / Limited Edition', readonly=True)

    # def _select_sale(self):
    #     select_ = super(SaleReport, self)._select_sale()
    #     select_ += """
    #         ,p.status
    #         ,p.barcode
    #         ,p.default_code
    #         ,t.product_sub_categ_1 AS product_sub_categ_1
    #         ,t.product_sub_categ_2 AS product_sub_categ_2
    #         ,t.is_gift AS is_gift
    #         ,t.product_group_id AS product_group_id
    #         ,t.release_id AS release_id
    #         ,t.collection_id AS collection_id
    #         ,t.production_edition AS production_edition
    #         ,COUNT(CASE WHEN p.status = 'active' THEN 1 END) AS status_active_count
    #         ,COUNT(CASE WHEN p.status = 'discontinued' THEN 1 END) AS status_discontinued_count
    #     """
    #     return select_

    # def _from_sale(self):
    #     return """
    #         sale_order_line l
    #         LEFT JOIN sale_order s ON s.id=l.order_id
    #         JOIN res_partner partner ON s.partner_id = partner.id
    #         LEFT JOIN product_product p ON l.product_id=p.id
    #         LEFT JOIN product_template t ON p.product_tmpl_id=t.id
    #         LEFT JOIN uom_uom u ON u.id=l.product_uom
    #         LEFT JOIN uom_uom u2 ON u2.id=t.uom_id
    #         LEFT JOIN product_category c1 ON t.product_sub_categ_1 = c1.id
    #         LEFT JOIN product_category c2 ON t.product_sub_categ_2 = c2.id
    #         JOIN {currency_table} ON currency_table.company_id = s.company_id
    #     """.format(
    #         currency_table=self.env['res.currency']._get_query_currency_table(self.env.companies.ids,
    #                                                                           fields.Date.today())
    #     )

    # def _group_by_sale(self):
    #     group_by_ = super(SaleReport, self)._group_by_sale()
    #     group_by_ += """
    #         ,p.status
    #         ,p.barcode
    #         ,p.default_code
    #         ,t.product_sub_categ_1
    #         ,t.product_sub_categ_2
    #         ,t.is_gift
    #         ,t.product_group_id
    #         ,t.release_id
    #         ,t.collection_id
    #         ,t.production_edition
    #     """
    #     return group_by_
    #



