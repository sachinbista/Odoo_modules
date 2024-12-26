from odoo import api, fields, models, tools
from six import string_types


class AgedInventoryReport(models.Model):
    _name = "aged.inventory.report"
    _description = "Aged Inventory Report"
    _auto = False

    # Purchase Report Part
    po_date_order = fields.Datetime('PO Order Date', readonly=True, help="Date on which this document has been created")
    purchase_state = fields.Selection([
        ('draft', 'Draft RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Order Status', readonly=True)
    picking_type_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    vendor_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    date_approve = fields.Date('Date Approved', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    po_user_id = fields.Many2one('res.users', 'Responsible', readonly=True)
    delay = fields.Float('Days to Validate', digits=(16, 2), readonly=True)
    delay_pass = fields.Float('Days to Deliver', digits=(16, 2), readonly=True)
    unit_quantity = fields.Float('PO Product Quantity', readonly=True)
    purchase_price_total = fields.Float('Purchase Total Price', readonly=True)
    price_average = fields.Float('Average Price', readonly=True, group_operator="avg")
    negociation = fields.Float('Purchase-Standard Price', readonly=True, group_operator="avg")
    price_standard = fields.Float('Products Value', readonly=True, group_operator="sum")
    nbr_lines = fields.Integer('# of Lines', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    # Sale Report Part
    name = fields.Char('SO Reference', readonly=True)
    so_order_date = fields.Datetime('SO Order Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('# of Qty', readonly=True)
    qty_delivered = fields.Float('Qty Delivered', readonly=True)
    qty_to_invoice = fields.Float('Qty To Invoice', readonly=True)
    qty_invoiced = fields.Float('Qty Invoiced', readonly=True)
    customer_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    so_user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    sale_price_total = fields.Float('Sales Total', readonly=True)
    price_subtotal = fields.Float('Sales Untaxed Total', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    nbr = fields.Integer('# of Lines', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    country_id = fields.Many2one('res.country', 'Partner Country', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Commercial Entity', readonly=True)
    sale_state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
    ], string='Sale Status', readonly=True)
    weight = fields.Float('Gross Weight', readonly=True)
    volume = fields.Float('Volume', readonly=True)
    location_id = fields.Many2one('stock.location', 'Location', auto_join=True, index=True, ondelete="restrict",
                                  readonly=True, required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number', index=True, ondelete="restrict",
                             readonly=True)
    in_date = fields.Datetime('Incoming Date', index=True, readonly=True)
    expiry_date = fields.Datetime('Expiry Date', index=True, readonly=True)
    qty = fields.Float('Positive Stock Quantity', index=True, readonly=True, required=True)
    neg_qty = fields.Float('Negative Stock Quantity', index=True, readonly=True, required=True)
    age = fields.Integer('Age', index=True, readonly=True, required=True)

    # Product Margin
    sale_avg_price = fields.Float(string='Avg. Unit Price', help="Avg. Price in Customer Invoices.", readonly=True)
    purchase_avg_price = fields.Float(string='Avg. Unit Price', help="Avg. Price in Vendor Bills ", readonly=True)
    sale_num_invoiced = fields.Float(string='# Invoiced in Sale', help="Sum of Quantity in Customer Invoices",
                                     readonly=True)
    purchase_num_invoiced = fields.Float(string='# Invoiced in Purchase', help="Sum of Quantity in Vendor Bills",
                                         readonly=True)
    sales_gap = fields.Float(string='Sales Gap', help="Expected Sale - Turn Over", readonly=True)
    # purchase_gap = fields.Float(string='Purchase Gap', help="Normal Cost - Total Cost", readonly=True)
    turnover = fields.Float(string='Turnover',
                            help="Sum of Multiplication of Invoice price and quantity of Customer Invoices",
                            readonly=True)
    total_cost = fields.Float(string='Total Cost',
                              help="Sum of Multiplication of Invoice price and quantity of Vendor Bills ",
                              readonly=True)
    sale_expected = fields.Float(string='Expected Sale',
                                 help="Sum of Multiplication of Sale Catalog price and quantity of Customer Invoices",
                                 readonly=True)
    normal_cost = fields.Float(string='Normal Cost',
                               help="Sum of Multiplication of Cost price and quantity of Vendor Bills", readonly=True)
    # total_margin = fields.Float(string='Total Margin', help="Turnover - Standard price", readonly=True)
    # expected_margin = fields.Float(string='Expected Margin', help="Expected Sale - Normal Cost", readonly=True)
    # total_margin_rate = fields.Float(string='Total Margin Rate(%)', help="Total margin * 100 / Turnover", readonly=True)
    # expected_margin_rate = fields.Float(string='Expected Margin (%)', help="Expected margin * 100 / Expected Sale", readonly=True)
    date_invoice = fields.Date(string='Invoice Date', readonly=True)
    invoice_state = fields.Selection([('draft', 'Draft'), ('proforma', 'Pro-forma'), ('proforma2', 'Pro-forma'),
                                      ('open', 'Open'), ('paid', 'Paid'), ('cancel', 'Cancelled'), ],
                                     string='Inv. Status', readonly=True)
    invoice_type = fields.Selection([('out_invoice', 'Customer Invoice'), ('in_invoice', 'Vendor Bill'),
                                     ('out_refund', 'Customer Refund'), ('in_refund', 'Vendor Refund'), ],
                                    string="Inv. Type", readonly=True)

    # @api.model
    # def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     self.check_access_rights('read')
    #     query = self._where_calc(domain)
    #     fields = fields or [f.name for f in self._fields.itervalues() if f.store]
    #
    #     groupby = [groupby] if isinstance(groupby, string_types) else list(tools.OrderedSet(groupby))
    #     groupby_list = groupby[:1] if lazy else groupby
    #     annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
    #     groupby_fields = [g['field'] for g in annotated_groupbys]
    #     order = orderby or ','.join([g for g in groupby_list])
    #     groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}
    #
    #     self._apply_ir_rules(query, 'read')
    #     for gb in groupby_fields:
    #         assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
    #         assert gb in self._fields, "Unknown field %r in 'groupby'" % gb
    #         gb_field = self._fields[gb].base_field
    #         assert gb_field.store and gb_field.column_type, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"
    #
    #     aggregated_fields = [
    #         f for f in fields
    #         if f != 'sequence'
    #         if f not in groupby_fields
    #         for field in [self._fields.get(f)]
    #         if field
    #         if field.group_operator
    #         if field.base_field.store and field.base_field.column_type
    #     ]
    #
    #     field_formatter = lambda f: (
    #         self._fields[f].group_operator,
    #         self._inherits_join_calc(self._table, f, query),
    #         f,
    #     )
    #     select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]
    #
    #     for gb in annotated_groupbys:
    #         select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))
    #     groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
    #     from_clause, where_clause, where_clause_params = query.get_sql()
    #     if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
    #         count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
    #     else:
    #         count_field = '_'
    #     count_field += '_count'
    #
    #     prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
    #     prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''
    #     if self._name == 'aged.inventory.report':
    #         select_terms.append('aged_inventory_report.in_date as in_date, aged_inventory_report.expiry_date as expiry_date')
    #         groupby_terms.append('aged_inventory_report.in_date, aged_inventory_report.expiry_date',)
    #
    #     query = """
    #         SELECT min("%(table)s".id) AS id, count("%(table)s".id) AS "%(count_field)s" %(extra_fields)s
    #         FROM %(from)s
    #         %(where)s
    #         %(groupby)s
    #         %(orderby)s
    #         %(limit)s
    #         %(offset)s
    #     """ % {
    #         'table': self._table,
    #         'count_field': count_field,
    #         'extra_fields': prefix_terms(',', select_terms),
    #         'from': from_clause,
    #         'where': prefix_term('WHERE', where_clause),
    #         'groupby': prefix_terms('GROUP BY', groupby_terms),
    #         'orderby': prefix_terms('ORDER BY', orderby_terms),
    #         'limit': prefix_term('LIMIT', int(limit) if limit else None),
    #         'offset': prefix_term('OFFSET', int(offset) if limit else None),
    #     }
    #     self._cr.execute(query, where_clause_params)
    #     fetched_data = self._cr.dictfetchall()
    #
    #     if not groupby_fields:
    #         return fetched_data
    #
    #     many2onefields = [gb['field'] for gb in annotated_groupbys if gb['type'] == 'many2one']
    #     if many2onefields:
    #         data_ids = [r['id'] for r in fetched_data]
    #         many2onefields = list(set(many2onefields))
    #         data_dict = {d['id']: d for d in self.browse(data_ids).read(many2onefields)}
    #         for d in fetched_data:
    #             d.update(data_dict[d['id']])
    #
    #     data = map(lambda r: {k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.iteritems()}, fetched_data)
    #     result = [self._read_group_format_result(d, annotated_groupbys, groupby, domain) for d in data]
    #     if lazy:
    #         # Right now, read_group only fill results in lazy mode (by default).
    #         # If you need to have the empty groups in 'eager' mode, then the
    #         # method _read_group_fill_results need to be completely reimplemented
    #         # in a sane way
    #         result = self._read_group_fill_results(
    #             domain, groupby_fields[0], groupby[len(annotated_groupbys):],
    #             aggregated_fields, count_field, result, read_group_order=order,
    #         )
    #     return result

    def _select(self):
        select_str = """
            WITH currency_rate as (%s)
            SELECT min(p.id) as id,
            p.id as product_id,
            p.product_tmpl_id as product_tmpl_id,
            quant.in_date AS in_date,
            quant.expiry_date AS expiry_date,
            quant.location_id AS location_id,
            quant.lot_id AS lot_id,
            t.uom_id as uom_uom,
            sum(sol.product_uom_qty) as product_uom_qty,
            sum(sol.qty_delivered) as qty_delivered,
            sum(sol.qty_invoiced) as qty_invoiced,
            sum(sol.qty_to_invoice) as qty_to_invoice,
            sum(sol.price_total / COALESCE(cr.rate, 1.0)) as sale_price_total,
            sum(sol.price_subtotal / COALESCE(cr.rate, 1.0)) as price_subtotal,
            count(*) as nbr,
            so.name as name,
            so.date_order as so_order_date,
            so.state as sale_state,
            so.partner_id as customer_id,
            so.user_id as so_user_id,
            so.company_id as company_id,
            t.categ_id as categ_id,
            so.pricelist_id as pricelist_id,
            so.analytic_account_id as analytic_account_id,
            so.team_id as team_id,
            partner.country_id as country_id,
            partner.commercial_partner_id as commercial_partner_id,
            sum(p.weight * sol.product_uom_qty) as weight,
            sum(p.volume * sol.product_uom_qty) as volume,
            po.date_order as po_date_order,
            po.state as purchase_state,
            po.date_approve as date_approve,
            po.dest_address_id,
            spt.warehouse_id as picking_type_id,
            po.partner_id as vendor_id,
            po.create_uid as po_user_id,
            po.fiscal_position_id as fiscal_position_id,
            po.currency_id,
            sum(pol.product_qty) as unit_quantity,
            extract(epoch from age(po.date_approve,po.date_order))/(24*60*60)::decimal(16,2) as delay,
            extract(epoch from age(pol.date_planned,po.date_order))/(24*60*60)::decimal(16,2) as delay_pass,
            count(*) as nbr_lines,
            sum(pol.price_unit / COALESCE(cr.rate, 1.0) * pol.product_qty)::decimal(16,2) as purchase_price_total,
            avg(100.0 * (pol.price_unit / COALESCE(cr.rate,1.0) * pol.product_qty) / NULLIF(ip.value_float*pol.product_qty, 0.0))::decimal(16,2) as negociation,
            sum(ip.value_float*pol.product_qty)::decimal(16,2) as price_standard,
            (sum(pol.product_qty * pol.price_unit / COALESCE(cr.rate, 1.0))/NULLIF(sum(pol.product_qty),0.0))::decimal(16,2) as price_average,
            COALESCE(cast(to_char(date_trunc('day',CURRENT_DATE) - date_trunc('day',quant.in_date),'DD') AS INT),1) as age,
            CASE WHEN quant.quantity > 0.0 AND sl.usage='internal' THEN quant.quantity ELSE 0.0 END AS qty,
            CASE WHEN quant.quantity < 0.0 AND sl.usage='internal' THEN quant.quantity ELSE 0.0 END AS neg_qty,
            sum(p.std_price * ail.quantity) as normal_cost,
            sum(ail.price_unit * ail.quantity)/nullif(sum(ail.quantity),0) as sale_avg_price,
            sum(ail.quantity) as sale_num_invoiced,
            sum(ail.quantity * (ail.price_subtotal/(nullif(ail.quantity,0)))) as turnover,
            sum(ail.quantity * t.list_price) as sale_expected,
            (sum(ail.quantity * t.list_price)- sum(ail.quantity * (ail.price_subtotal/(nullif(ail.quantity,0))))) as sales_gap,
            ai.invoice_date as date_invoice,
            ai.state as invoice_state,
            ai.move_type as invoice_type,
            case when ai.move_type = 'in_invoice' then
            sum(ail.price_unit * ail.quantity)/nullif(sum(ail.quantity),0) end as purchase_avg_price,
            case when ai.move_type = 'in_invoice' then 
                sum(ail.quantity) end as purchase_num_invoiced,
            case when ai.move_type = 'in_invoice' then 
            sum(ail.quantity * (ail.price_subtotal/(nullif(ail.quantity,0))))  end as total_cost

        """ % self.env['res.currency']._select_companies_rates()
        return select_str

    def _from(self):
        from_str = """
                product_product p
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join stock_quant quant on (quant.product_id=p.id)
                    left join stock_location sl on (quant.location_id=sl.id)
                    left join account_move_line ail on (ail.product_id=p.id)
                    left join account_move ai on (ail.move_id = ai.id) AND ai.move_type IN ('in_invoice', 'out_refund')
                    left join sale_order_line sol on (sol.product_id=p.id)
                    left join sale_order so on (sol.order_id=so.id)
                    left join uom_uom u on (u.id=t.uom_id)
                    left join product_pricelist pp on (so.pricelist_id = pp.id)
                    left join purchase_order_line pol on (pol.product_id=p.id)
                    left join purchase_order po on (pol.order_id=po.id)
                    left join res_partner partner on so.partner_id = partner.id
                        LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id=CONCAT('product.template,',t.id) AND ip.company_id=so.company_id)
                    left join stock_picking_type spt on (spt.id=po.picking_type_id)
                    left join currency_rate cr on (cr.currency_id = pp.currency_id and
                        cr.company_id = so.company_id and
                        cr.date_start <= coalesce(so.date_order, now()) and
                        (cr.date_end is null or cr.date_end > coalesce(po.date_order, now())))
        """
        return from_str

    # def _where(self):
    #     where_str = """
    #         ai1.type IN ('out_invoice', 'in_refund')
    #     """
    #     return where_str

    def _group_by(self):
        group_by_str = """
            GROUP BY p.id,
            p.product_tmpl_id,
            quant.in_date,
            quant.expiry_date,
            quant.location_id,
            quant.lot_id,
            quant.quantity,
            sl.usage,
            ai.invoice_date,
            ai.state,
            ai.move_type,
            t.uom_id,
            so.name,
            so.date_order,
            so.state,
            so.partner_id,
            so.user_id,
            so.company_id,
            t.categ_id,
            so.pricelist_id,
            so.analytic_account_id,
            so.team_id,
            partner.country_id,
            partner.commercial_partner_id,
            po.date_order,
            po.state,
            po.date_approve,
            po.dest_address_id,
            spt.warehouse_id,
            po.partner_id,
            po.create_uid,
            po.fiscal_position_id,
            po.currency_id,
            pol.date_planned
        """
        return group_by_str

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s FROM ( %s ) %s)""" % (
        self._table, self._select(), self._from(), self._group_by()))
