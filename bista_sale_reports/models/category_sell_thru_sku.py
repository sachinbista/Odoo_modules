# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import pytz
from operator import itemgetter
from odoo import models, fields, api, _


class CategorySellThruSKU(models.AbstractModel):
    _name = "category.sell.thru.sku"
    _description = "Category Sell-thru SKU Report"

    _inherit = 'account.report.custom.handler'

    filter_date = {'mode': 'range', 'date_from': '', 'date_to': '', 'filter': 'this_month'}
    filter_category = True
    filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
    filter_ownership = [{'id': 'All', 'name': _('All'), 'selected': True},
                        {'id': 'Memo', 'name': _('Memo'), 'selected': False},
                        {'id': 'Owned', 'name': _('Owned'), 'selected': False}]

    def _build_options(self, previous_options=None):
        self.filter_ownership = [{'id': 'All', 'name': _('All'), 'selected': True},
                                 {'id': 'Memo', 'name': _('Memo'), 'selected': False},
                                 {'id': 'Owned', 'name': _('Owned'), 'selected': False}]
        return super(CategorySellThruSKU, self)._build_options(previous_options=previous_options)

    # ===========================================================================
    # Function for finding vendor details based on vendor procelist
    # ===========================================================================
    def get_available_vendor_ids(self, ids=None):
        vendor_ids = []
        for vendor_pricelist in self.env['product.supplierinfo'].search([('partner_id', '!=', False)]):
            vendor_ids.append(vendor_pricelist.partner_id)
        vendor_ids = vendor_ids and list(set(vendor_ids)) or []
        list_to_be_sorted = [{'id': c.id, 'name': c.name} for c in vendor_ids]
        sorted_list = sorted(list_to_be_sorted, key=itemgetter('name'))
        sorted_vendors_ids = [x['id'] for x in sorted_list]
        if ids:
            return sorted_vendors_ids
        else:
            return self.env['res.partner'].browse(sorted_vendors_ids)

    # ===========================================================================
    # function for gettig the vendor ids
    # ===========================================================================
    def get_product_ids(self, date_from, date_to, vendor_ids):
        context = self.env.context

        category_ids = context.get('category_ids', False)
        if vendor_ids:
            vendor_ids = vendor_ids
        else:
            vendor_ids = self.get_available_vendor_ids().ids

        vendor_ids_str = ','.join(str(x) for x in vendor_ids)
        vendor_ids = '(' + str(vendor_ids_str) + ')'
        product_ids = []
        if category_ids:
            category_ids_str = ','.join(str(x) for x in category_ids.ids)
            category_ids = '(' + category_ids_str + ')'

            sql = ("""
                select 
                    pp.id 
                from product_product pp 
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                    inner join stock_move sm on(sm.product_id = pp.id)
                    inner join stock_picking sp on (sp.id = sm.picking_id)
                where sp.date_done >='%s' and sp.date_done<='%s' and  pt.categ_id in %s and 
                    psi.id in %s order by psi.product_code asc
                """) % (date_from, date_to, category_ids, vendor_ids)

        else:

            sql = ("""
                select 
                    pp.id 
                from product_product pp 
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                    inner join stock_move sm on(sm.product_id = pp.id)
                    inner join stock_picking sp on (sp.id = sm.picking_id)
                where sp.date_done >='%s' and sp.date_done<='%s' and
                    psi.id in %s order by psi.product_code asc
                """) % (date_from, date_to, vendor_ids)

        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            if id[0] not in product_ids:
                product_ids += id
        return product_ids

    # ===========================================================================
    # Function for add timezone with given date
    # ===========================================================================
    def get_date_with_tz(self, date):
        datetime_with_tz = pytz.timezone(self._context['tz']).localize(fields.Datetime.from_string(date),
                                                                       is_dst=None)  # No daylight saving time
        datetime_in_utc = datetime_with_tz.astimezone(pytz.utc)
        date = datetime_in_utc.strftime('%Y-%m-%d %H:%M:%S')
        return date
        # ===========================================================================

    # Function for finding the purchase amount of given duration for given product
    # ===========================================================================
    def get_purchase_amount(self, date_from, date_to, product_id=None):
        sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('incoming') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('outgoing') THEN -(sm.product_uom_qty)
                            ELSE 0
                       END) as net_qty
                    ,SUM((sol.price_unit*CASE WHEN spt.code in ('incoming') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('outgoing') THEN -(sm.product_uom_qty)
                            ELSE 0
                       END)) as invoice_price 
                from purchase_order_line sol
                    inner join purchase_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                where 
                    sp.date_done >= '2018-08-01' and sp.date_done <= '2018-08-31' and 
                    sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id 
            """) % (date_from, date_to)
        if product_id:
            sql += (' and sm.product_id=%s') % (product_id)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        invoice_sale = 0
        for value in result:
            invoice_sale += value.get('invoice_price', 0) or 0
        return invoice_sale

        # ===========================================================================

    # function for calculate sales amount based on the inputs given
    # ===========================================================================
    def get_sale_amount(self, date_from, date_to, product_id=None):
        context = self.env.context

        sql = ("""
        SELECT      SUM(CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty)  WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty) ELSE 0  END) as net_qty

      ,SUM(case when pt.list_price = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty)
                    ELSE 0 END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty) ELSE 0 END) end) as sale_price

      ,SUM(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty) ELSE 0
               END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty)
                    ELSE 0 END)* (1- sol.discount))/100.0 end) as invoice_price 

      ,SUM(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty)
                    ELSE 0 END) end) as cost_price

      ,SUM(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty)
           ELSE 0 END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty)
           ELSE 0 END)* (1- sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sol.product_uom_qty)
           WHEN spt.code in ('incoming') THEN -(sol.product_uom_qty) ELSE 0 END) end)  as gross_margin
	    from sale_order_line sol
            inner join sale_order so on (so.id = sol.order_id)
            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)

            inner join product_product pp on (sol.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join res_partner rp on (rp.id = so.partner_id)

        where sp.date_done >= '%s' and sp.date_done <= '%s' 
            and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
        """) % (date_from, date_to)

        if product_id:
            sql += ('and sol.product_id = %s' % (product_id))
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        retail_sale = 0
        invoice_sale = 0
        product_count = 0
        cost_price = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
        return [cost_price, invoice_sale, retail_sale, product_count]

    def get_sale_amount_of_pos(self, date_from, date_to, product_id=None):
        context = self.env.context

        sql = ("""
        select 

            SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0 END) as net_qty

            ,sum(case when pt.list_price = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0 END) 
                    else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) end) as sale_price

            ,sum(case when pol.discount = 0.0 then (pol.price_unit * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END)

                else ( (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)  ELSE 0  END) ) end * (100 - pol.discount) /100.0 
               ) as invoice_price 

            ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0  END) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) else ((pol.price_unit*sm.product_uom_qty)* (100 - pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin

           from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
        where sp.date_done >= '%s' and sp.date_done <= '%s'
            and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = pol.product_id
        """) % (date_from, date_to)
        if product_id:
            sql += ('and pol.product_id = %s' % (product_id))

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        retail_sale = 0
        invoice_sale = 0
        product_count = 0
        cost_price = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0

        return [cost_price, invoice_sale, retail_sale, product_count]

    # ===========================================================================
    # Function for getting total available quantity in the stock
    # ===========================================================================
    def get_total_onhand_product(self):
        available_qty = 0
        for product in self.env['product.product'].search([('qty_available', '>', 0)]):
            if product.qty_available:
                available_qty += product.qty_available
        return available_qty

    # ===========================================================================
    # Function for getting the available quantity of the product
    # ===========================================================================
    def get_onhand_product(self, product=None, lot_id=None):
        available_qty = 0
        product_cost_amount = 0
        product_retail_amount = 0

        sql = ("""
            select 
                sq.quantity as qty
                ,sq.quantity* pp.std_price as cost_price
                ,sq.quantity* pt.list_price as sale_price
                from stock_quant sq
                INNER JOIN product_product pp on (pp.id = sq.product_id)
                INNER JOIN stock_location sl on (sl.id=sq.location_id)
                INNER JOIN product_template pt on (pp.product_tmpl_id = pt.id)
                where sl.usage = 'internal'
        """)
        if product:
            sql += (' and sq.product_id= %s') % (product.id)
        if lot_id:
            sql += (' and sq.lot_id= %s') % (lot_id)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        for val in result:
            available_qty += val.get('qty', 0) or 0
            product_cost_amount += val.get('cost_price', 0) or 0
            product_retail_amount += val.get('sale_price', 0) or 0
        #
        return [available_qty, product_retail_amount, product_cost_amount]

    def get_available_lots(self, date_from, date_to, product_id):
        result = []
        sql = ("""
            select 
                SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) as net_qty
                ,spl.id as lot_id
                ,sum(case when pt.list_price = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) end) as sale_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END)* (1- sol.discount))/100.0 end) as invoice_price 
                ,sum(pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) as cost_price
            from sale_order_line sol
                inner join sale_order so on (so.id = sol.order_id)
                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                inner join stock_move sm on (sp.id = sm.picking_id)
                inner join res_partner rp on (rp.id = so.partner_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join stock_quant_move_rel sqmr on (sqmr.move_id = sm.id)
                inner join stock_quant sq on (sq.id = sqmr.quant_id)
                inner join stock_production_lot spl on (spl.id = sq.lot_id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where 
                sp.date_done >= '%s' and sp.date_done <= '%s' 
                and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id 
                and pt.exclude_from_report = False and pc.sale_type = 'sale' and sol.product_id = %s
                 group by spl.id
        """) % (date_from, date_to, product_id)
        self._cr.execute(sql)
        res = self._cr.dictfetchall()

        product_count = 0
        lot_id = 0
        for value in res:
            product_count = value.get('net_qty', 0) or 0
            lot_id = value.get('lot_id', 0) or 0
            # result.append(lot_id)

        if lot_id and product_count:
            result.append(lot_id)

        return result

        # ===========================================================================

    # Function for getting serial number wise sale order details
    # ===========================================================================
    def get_lot_sale_order(self, date_from, date_to, product_id=None, lot_id=None):
        result = [0, 0, 0, 0]
        lot_id_clause = ''
        if lot_id:
            lot_id_clause = (""" and spl.id = %s""") % (lot_id)
        if product_id:

            sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                    ELSE 0
                               END) as net_qty
                    ,spl.id as lot_id
                    ,sum(case when pt.list_price = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                    ELSE 0
                               END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                    ELSE 0
                               END) end) as sale_price
                    ,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                    ELSE 0
                               END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                    ELSE 0
                               END)* (1- sol.discount))/100.0 end) as invoice_price 
                    ,sum(pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                    ELSE 0
                               END) as cost_price
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join stock_quant_move_rel sqmr on (sqmr.move_id = sm.id)
                    inner join stock_quant sq on (sq.id = sqmr.quant_id)
                    inner join stock_production_lot spl on (spl.id = sq.lot_id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where 
                    sp.date_done >= '%s' and sp.date_done <= '%s' and 
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id 
                    and pt.exclude_from_report = False and pc.sale_type = 'sale' and sol.product_id = %s %s
                     group by spl.id
            """) % (date_from, date_to, product_id, lot_id_clause)

            self._cr.execute(sql)
            res = self._cr.dictfetchall()

            retail_sale = 0
            invoice_sale = 0
            product_count = 0
            cost_price = 0
            for value in res:
                retail_sale = value.get('sale_price', 0) or 0
                cost_price = value.get('cost_price', 0) or '0'
                invoice_sale = value.get('invoice_price', 0) or 0
                product_count = value.get('net_qty', 0) or 0
                lot_id = value.get('lot_id', 0) or 0
            if lot_id and product_count:
                result = [cost_price, invoice_sale, retail_sale, product_count]
        return result

    # ===========================================================================
    # Function for format amount with 2 decimal & grouping is based on the language settings
    # ===========================================================================
    def format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True).replace(r' ',
                                                                                         u'\N{NO-BREAK SPACE}').replace(
            r'-', u'\u2011')
        return formatted_amount

    def get_vendor_reference(self, product):
        ref = ''
        if product:
            if product.product_vendor_code:
                ref = product.product_vendor_code
            else:
                for pricelist in product.seller_ids:
                    if pricelist.product_code:
                        ref = pricelist.product_code
                        break
        return ref

    def get_product_owner(self, product_id):
        # owner_id =self.env.user.company_id.partner_id
        owner_id = 'Owned'
        quants = self.env['stock.quant'].search([('product_id', '=', product_id), ('owner_id', '!=', False)], limit=1)
        if quants:
            owner_id = 'Memo'

        return owner_id

    @api.model
    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):

        context = self.env.context
        date_from = context.get('date_from', False)
        date_from = context.get('date_from', False)
        if not date_from:
            if options.get('date') and options['date'].get('date_from'):
                date_from = options['date']['date_from']

        date_to = context.get('date_to', False)
        if not date_to:
            if options.get('date'):
                date_to = options['date'].get('date_to') or options['date'].get('date')

        if date_from:
            date_from = str(date_from) + ' 00:00:00'
        if date_to:
            date_to = str(date_to) + ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        periods = options['comparison'].get('periods')
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        lines = []
        line_id = 0

        columns_header = [
            {'name': _('Owner')},
            {'name': _('Vendor Ref/Serial #')},
            {'name': _('% SellThru')},
        ]
        period_columns = []
        if options.get('comparison') and options.get('comparison').get('periods'):

            for period in options.get('comparison').get('periods'):
                if period.get('string') != 'initial':
                    period_columns += [
                        {'name': _('$ Sold'), 'class': 'number'},
                        {'name': _('# Sold'), 'class': 'number'},
                        {'name': _('% Disc'), 'class': 'number'},
                    ]

        columns_header += [
            {'name': _('% Sales')},
            {'name': _('$ Sold')},
            {'name': _('$ Retail')},
            {'name': _('# Sold')},
            {'name': _('% Disc')},
            {'name': _('Avg Sale')},
            {'name': _('DTS')},
            {'name': _('COGS')},
            {'name': _('$ GM')},
            {'name': _('% GM')},
        ]

        lines.append({
            'id': line_id,
            'name': _('Internal Ref'),
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': columns_header + period_columns,
            'title_hover': _('Header'),
            'level': 2
        })
        line_id += 1

        ownership = 'All'
        if options.get('ownership'):
            for option in options.get('ownership'):
                if option.get('selected') == True:
                    ownership = option.get('id')

        total_invoice_amount = self.get_sale_amount(date_from, date_to)[1]
        total_invoice_amount_pos = self.get_sale_amount_of_pos(date_from, date_to)[1]

        total_invoice_amount = total_invoice_amount + total_invoice_amount_pos
        total_qty_available = self.get_total_onhand_product()
        sale_purchase_perc_sum = 0
        sale_perc_sum = 0
        invoice_sale_sum = {}
        product_count_sum = {}
        retail_sale_sum = {}
        product_cost_sum = 0
        gross_margin_sum = 0
        product_available_qty_sum = 0
        product_available_qty_perc_sum = 0
        product_available_product_price_sum = 0
        product_avg_on_hand_price_sum = 0
        # initialize dictionary variable with zero based on periods
        periods = self.remove_duplicated_period(periods)

        for period in periods:
            period_date_from = period.get('date_from')
            invoice_sale_sum[period_date_from] = 0
            product_count_sum[period_date_from] = 0
            retail_sale_sum[period_date_from] = 0

        vendor_ids = options.get('partner_ids', [])
        print(">>................vendor_ids.........", vendor_ids)
        product_ids = self.get_product_ids(date_from, date_to, vendor_ids)
        for product in self.env['product.product'].browse(product_ids):
            column = []

            stop_current_execution = False

            owner = self.get_product_owner(product_id=product.id)

            if ownership in ['Memo', 'Owned']:
                if ownership == 'Memo' and 'Owned' == owner:
                    continue
                elif ownership == 'Owned' and 'Memo' == owner:
                    continue

            def insert_newline(string, index, addin):
                return string[:index] + addin + string[index:]

            product_name = product.name
            quo = int(len(product.name) / 25) + 1
            for x in range(quo):
                index = (x + 1) * 25 + x
                product_name = insert_newline(product_name, index, '<br/>')

            for period in periods:
                period_date_from = period.get('date_from')
                period_date_to = period.get('date_to')

                product_sale_amount_list = self.get_sale_amount(period_date_from, period_date_to, product_id=product.id)
                product_sale_amount_list_pos = self.get_sale_amount_of_pos(period_date_from, period_date_to,
                                                                           product_id=product.id)

                product_sale_amount_list[0] = product_sale_amount_list[0] + product_sale_amount_list_pos[0]
                product_sale_amount_list[1] = product_sale_amount_list[1] + product_sale_amount_list_pos[1]
                product_sale_amount_list[2] = product_sale_amount_list[2] + product_sale_amount_list_pos[2]
                product_sale_amount_list[3] = product_sale_amount_list[3] + product_sale_amount_list_pos[3]
                product_cost_amount = product_sale_amount_list[0]
                product_invoice_amount = product_sale_amount_list[1]
                product_retail_sale = product_sale_amount_list[2]
                product_product_count = product_sale_amount_list[3]

                if period_date_from == date_from:

                    if not product_product_count:
                        stop_current_execution = True
                        break
                    product_list = self.get_onhand_product(product=product)
                    onhand_product_cost_amount = product_list[2] or 0
                    sale_purchase_perc = 0
                    if not product_cost_amount + onhand_product_cost_amount == 0:
                        sale_purchase_perc = product_cost_amount and product_cost_amount / (
                                product_cost_amount + onhand_product_cost_amount) or 0
                    sale_purchase_perc_sum += onhand_product_cost_amount
                    sale_purchase_perc = str(self.format_value(round(sale_purchase_perc * 100, 2))) + '%'

                    product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                    product_sale_perc = str(self.format_value(round(product_perc * 100, 2))) + '%'
                    sale_perc_sum += product_perc

                    column = [{'name': owner}, {'name': self.get_vendor_reference(product)},
                              {'name': sale_purchase_perc}, {'name': product_sale_perc}]

                invoice_sale_sum[period_date_from] += product_invoice_amount
                product_count_sum[period_date_from] += product_product_count
                retail_sale_sum[period_date_from] += product_retail_sale

                product_invoice_amount_formatted = self.format_value(product_invoice_amount)
                product_discount = product_retail_sale and (
                        product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                product_discount_perc = str(self.format_value(round(product_discount * 100, 2))) + '%'
                column += [{'name': product_invoice_amount_formatted}, {'name': self.format_value(product.lst_price)},
                           {'name': product_product_count}, {'name': product_discount_perc}]
                if period_date_from == date_from:
                    average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                    gross_margin = product_invoice_amount - product_cost_amount
                    gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0

                    product_cost_sum += product_cost_amount
                    gross_margin_sum += gross_margin

                    average_sale = self.format_value(average_sale)
                    product_cost_amount = self.format_value(product_cost_amount)
                    gross_margin = self.format_value(gross_margin)
                    gross_margin_perc = str(self.format_value(round(gross_margin_perc * 100, 2))) + '%'

                    column += [{'name': average_sale}, {'name': '0.00'}, {'name': product_cost_amount},
                               {'name': gross_margin}, {'name': gross_margin_perc}]

                    product_list = self.get_onhand_product(product=product)
                    product_available_qty = product_list[0]
                    product_available_product_price = product_list[1]
                    product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                    product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                    product_available_qty_sum += product_available_qty
                    product_available_qty_perc_sum += product_available_qty_perc
                    product_available_product_price_sum += product_available_product_price
                    product_avg_on_hand_price_sum += product_avg_on_hand_price

            if stop_current_execution:
                continue

            if product.default_code:

                lines.append({
                    'id': line_id,
                    'name': str('[' + product.default_code + '] ' + product.name[:35]) and str(
                        '[' + product.default_code or '' + '] ' + product.name[:35]) or '',
                    'unfoldable': False,
                    'columns': column,
                    'level': 3,

                })
            else:
                lines.append({
                    'id': line_id,
                    'name': str('[Sku Missing]' + product.name[:35]) and str(
                        '[Sku Missing] ' + product.name[:35]) or '',
                    'unfoldable': False,
                    'columns': column,
                    'level': 3,

                })

            line_id += 1

            available_serial_numbers = product.get_available_serial_numbers(date_from, date_to)
            if len(available_serial_numbers) > 0:
                for av_ser in available_serial_numbers:
                    serial_sale_data = product.get_serial_numbers_sale_data(av_ser)
                    serial_dis = ((product.list_price - serial_sale_data[2]) / product.list_price) * 100
                    serial_gm = serial_sale_data[2] - serial_sale_data[1]
                    serial_gm_per = (serial_gm / serial_sale_data[2]) * 100
                    owner = 'Owned'
                    if serial_sale_data[3]:
                        owner = 'Memo'

                    lines.append({
                        'id': line_id,
                        'name': _(''),
                        'unfoldable': False,
                        'columns': [

                            {'name': owner}, {'name': serial_sale_data[0]}, {'name': ''}, {'name': ''}, {'name': ''},
                            {'name': ''}, {'name': ''},
                            {'name': str(self.format_value(serial_dis)) + '%'},
                            # {'name':self.format_value(product.list_price)},
                            {'name': self.format_value(serial_sale_data[2])},
                            {'name': '0.00'},

                            {'name': self.format_value(serial_sale_data[1])},
                            {'name': self.format_value(serial_gm)},
                            {'name': str(self.format_value(serial_gm_per)) + '%'},
                        ],
                        'level': 4,
                    })

        # Total Row
        onhand_product_cost_amount = 0
        if not sale_purchase_perc_sum + product_cost_sum == 0:
            onhand_product_cost_amount = product_cost_sum and product_cost_sum / (
                    sale_purchase_perc_sum + product_cost_sum) or 0
        sale_purchase_perc_sum = str(self.format_value(round(onhand_product_cost_amount * 100, 2))) + '%'
        sale_perc_sum_perc = str(self.format_value(round(sale_perc_sum * 100, 2))) + '%'
        bottom_column = [{'name': ''}, {'name': ''}, {'name': sale_purchase_perc_sum}, {'name': sale_perc_sum_perc}]
        # iterate with periods
        periods = self.remove_duplicated_period(periods)

        for period in periods:
            period_date_from = period.get('date_from')

            discount_sum = retail_sale_sum[period_date_from] and (
                    retail_sale_sum[period_date_from] - invoice_sale_sum[period_date_from]) / retail_sale_sum[
                               period_date_from] or 0
            discount_sum_perc = str(self.format_value(round(discount_sum * 100, 2))) + '%'

            bottom_column += [{'name': self.format_value(invoice_sale_sum[period_date_from])}, {'name': ''},
                              {'name': product_count_sum[period_date_from]}, {'name': discount_sum_perc}]
            if period_date_from == date_from:
                average_sale_sum = product_count_sum[period_date_from] and (
                        invoice_sale_sum[period_date_from] / product_count_sum[period_date_from]) or 0

                gross_margin_sum = str(gross_margin_sum).replace(",", "")
                gross_margin_sum = float(gross_margin_sum)
                gross_margin_perc_sum = invoice_sale_sum[period_date_from] and gross_margin_sum / invoice_sale_sum[
                    period_date_from] or 0

                product_cost_sum = str(product_cost_sum).replace(",", "")
                product_cost_sum = float(product_cost_sum)

                product_available_qty_sum = str(product_available_qty_sum).replace(",", "")
                product_available_qty_sum = float(product_available_qty_sum)

                product_available_product_price_sum = str(product_available_product_price_sum).replace(",", "")
                product_available_product_price_sum = float(product_available_product_price_sum)

                average_sale_sum = self.format_value(average_sale_sum)
                product_cost_sum = self.format_value(product_cost_sum)
                gross_margin_sum = self.format_value(gross_margin_sum)
                gross_margin_perc_sum = str(self.format_value(round(gross_margin_perc_sum * 100, 2))) + '%'
                product_available_qty_sum = self.format_value(product_available_qty_sum)
                product_available_product_price_sum = self.format_value(product_available_product_price_sum)

                bottom_column += [{'name': average_sale_sum}, {'name': '0.00'}, {'name': product_cost_sum},
                                  {'name': gross_margin_sum}, {'name': gross_margin_perc_sum}]

        lines.append({
            'id': 'grouped_partners_total',
            'name': _('Total'),
            'unfoldable': False,
            'columns': bottom_column,
            'level': 1,
        })
        line_id += 1
        return [(0, line) for line in lines]

    def _get_report_name(self):
        return _('Category Sell Thru by SKU')

    def _get_columns_name(self, options):
        columns = [
            {'name': _(''), 'class': 'char'},
            {'name': _(''), 'class': 'char'},
            {'name': _(''), 'class': 'char'},
            {'name': _(''), 'class': 'number'},
        ]
        period_columns = []
        if options.get('comparison') and options.get('comparison').get('periods'):

            for period in options.get('comparison').get('periods'):
                if period.get('string') != 'initial':
                    period_columns += [
                        {'name': _(''), 'class': 'number'},
                        {'name': _(''), 'class': 'number'},
                        {'name': _(''), 'class': 'number'},
                    ]

        columns += [
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
            {'name': _(''), 'class': 'number'},
        ]
        return columns + period_columns

    def _get_reports_buttons(self):
        buttons = super(CategorySellThruSKU, self)._get_reports_buttons()
        return buttons

    def remove_duplicated_period(self, periods):
        seen = set()
        new_periods = []
        for d in periods:
            t = tuple(d.items())
            if t not in seen:
                seen.add(t)
                new_periods.append(d)

        return new_periods
