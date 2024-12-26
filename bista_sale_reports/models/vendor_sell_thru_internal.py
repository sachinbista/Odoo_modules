# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from datetime import datetime
from operator import itemgetter

import pytz
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, _


class VendorSellThroughInternal(models.AbstractModel):
    _name = 'vendor.sell.through.internal.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Vendor Sell Through Internal Handler'

    filter_date = {'mode': 'range', 'date_from': '', 'date_to': '', 'filter': 'this_month'}
    filter_partner = True
    filter_comparison = None
    filter_ownership = [{'id': 'All', 'name': _('All'), 'selected': True},
                        {'id': 'M', 'name': _('Memo'), 'selected': False},
                        {'id': 'O', 'name': _('Owned'), 'selected': False}]

    def get_sn_sp_all(self, options):
        context = self.env.context
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

        periods = options.get('comparison', False) and options.get('comparison', False).get('periods') or []
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        periods = self.remove_duplicated_period(periods)

        vendor_ids = options.get('partner_ids', [])

        product_ids = self.get_product_ids(date_from, date_to, vendor_ids)

        serial_numbers = []

        for product in self.env['product.product'].browse(product_ids):

            for period in periods:
                period_date_from = period.get('date_from')
                period_date_to = period.get('date_to')
                product_sale_amount_list = self.get_sale_amount(period_date_from, period_date_to, product_id=product.id)
                product_sale_amount_list_pos = self.get_sale_amount_of_pos(period_date_from, period_date_to,
                                                                           product_id=product.id)
                product_sale_amount_list[3] = product_sale_amount_list[3] + product_sale_amount_list_pos[3]

                product_product_count = product_sale_amount_list[3]

                if period_date_from == date_from:
                    if not product_product_count:
                        break
                    sn_sp_so = self.get_sn_sp_of_so(period_date_from, period_date_to, product_id=product.id)
                    sn_sp_pos = self.get_sn_sp_of_pos(period_date_from, period_date_to, product_id=product.id)
                    serial_numbers_all = sn_sp_so[0] + sn_sp_pos[0]
                    salesperson_all = sn_sp_so[1] + sn_sp_pos[1]
                    serial_numbers.append({product.id: [serial_numbers_all, salesperson_all]})
                # salespersons.append({product.id: salesperson_all})
        return serial_numbers

    def format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True).replace(r' ',
                                                                                         u'\N{NO-BREAK SPACE}').replace(
            r'-', u'\u2011')
        return formatted_amount

    def get_product_owner(self, product_id):
        # owner_id =self.env.user.company_id.partner_id
        owner_id = 'O'
        quants = self.env['stock.quant'].search([('product_id', '=', product_id), ('owner_id', '!=', False)], limit=1)
        if quants:
            owner_id = 'M'
        return owner_id

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

    def get_onhand_product_history(self, date_to, product_id=None):
        available_qty = 0
        product_cost_amount_total = 0
        sql = ("""
    			select
    				coalesce(sum(svl.quantity), 0.00) as qty
    				,coalesce(sum(svl.value), 0.00) as cost_price_total
    				from stock_valuation_layer svl
    			where
    				svl.product_id = %s and svl.create_date::DATE <= '%s'
    			group by svl.product_id
    		""") % (product_id, date_to)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        for val in result:
            available_qty += val.get('qty', 0) or 0
            product_cost_amount_total += val.get('cost_price_total', 0) or 0
        return [available_qty, product_cost_amount_total]

    def get_category_count_of_products(self, date_from, date_to, product_ids=None):
        product_ids_str = ','.join(str(x) for x in product_ids)
        product_ids = '(' + product_ids_str + ')'
        sql = ("""
            select SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) as net_qty
            from sale_order_line sol
                inner join sale_order so on (so.id = sol.order_id)
                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                inner join stock_move sm on (sp.id = sm.picking_id)
                inner join product_product pp on (sol.product_id = pp.id)
            where sp.date_done >= '%s' and sp.date_done <= '%s' 
                and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id
            """) % (date_from, date_to)

        if product_ids:
            sql += ('and sol.product_id in %s' % (product_ids))

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        count = 0
        for value in result:
            count += value.get('net_qty') or 0
        sql = ("""
                    select SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) as net_qty
                    from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    where sp.date_done >= '%s' and sp.date_done <= '%s' 
                        and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = pol.product_id
                    """) % (date_from, date_to)

        if product_ids:
            sql += ('and pol.product_id in %s' % (product_ids))

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        for value in result:
            count += value.get('net_qty') or 0

        return count

    def get_total_onhand_product(self):
        available_qty = 0
        for product in self.env['product.product'].search([('qty_available', '>', 0)]):
            if product.qty_available:
                available_qty += product.qty_available

        return available_qty

    def get_categ_all(self, options):
        context = self.env.context
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

        periods = options.get('comparison', False) and options.get('comparison', False).get('periods') or []
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        periods = self.remove_duplicated_period(periods)

        vendor_ids = options.get('partner_ids', [])

        product_ids = self.get_product_ids(date_from, date_to, vendor_ids)

        product_categ_ids = []
        for product in self.env['product.product'].browse(product_ids):
            for period in periods:
                period_date_from = period.get('date_from')
                period_date_to = period.get('date_to')
                product_sale_amount_list = self.get_sale_amount(period_date_from, period_date_to, product_id=product.id)
                product_sale_amount_list_pos = self.get_sale_amount_of_pos(period_date_from, period_date_to,
                                                                           product_id=product.id)
                product_sale_amount_list[3] = product_sale_amount_list[3] + product_sale_amount_list_pos[3]

                product_product_count = product_sale_amount_list[3]

                if period_date_from == date_from:
                    if not product_product_count:
                        break
                    product_categ_ids.append(product.product_tmpl_id.categ_id)

        product_categ_ids = list(set(product_categ_ids))

        all_categ = []
        all_parent_categ = []
        for value in product_categ_ids:
            l_categ = value.parent_path.split('/')
            all_parent_categ.append(value.parent_path.split('/')[0])
            all_categ.extend(l_categ[1:])
        all_categ = list(set(all_categ))
        all_parent_categ = list(set(all_parent_categ))
        return all_parent_categ, all_categ

    def get_date_with_tz(self, date):
        datetime_with_tz = pytz.timezone(self._context['tz']).localize(fields.Datetime.from_string(date),
                                                                       is_dst=None)  # No daylight saving time
        datetime_in_utc = datetime_with_tz.astimezone(pytz.utc)
        date = datetime_in_utc.strftime('%Y-%m-%d %H:%M:%S')

        return date

    def get_sn_sp_of_pos(self, date_from, date_to, product_id=None):
        if product_id:
            sql1 = ("""
    			select 
    				spl.name as serial_number
    			from pos_order_line pol
    				inner join pos_order po on (po.id = pol.order_id)
    				inner join stock_picking sp on (sp.pos_order_id = po.id)
    				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    				inner join stock_move sm on (sp.id = sm.picking_id)
    				inner join stock_move_line sml on (sml.move_id = sm.id)
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    			where sp.date_done >= '%s' and sp.date_done <= '%s' 
    				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = pol.product_id
    			""") % (date_from, date_to)
            sql1 += ('and pol.product_id = %s' % (product_id))
            sql2 = ("""
    			select 
    				po.cashier as salesperson
    			from pos_order_line pol
    				inner join pos_order po on (po.id = pol.order_id)
    				inner join stock_picking sp on (sp.pos_order_id = po.id)
    				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    				inner join stock_move sm on (sp.id = sm.picking_id)
    			where sp.date_done >= '%s' and sp.date_done <= '%s' 
    				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = pol.product_id
    			""") % (date_from, date_to)
            sql2 += ('and pol.product_id = %s' % (product_id))
            self._cr.execute(sql1)
            result1 = self._cr.dictfetchall()
            self._cr.execute(sql2)
            result2 = self._cr.dictfetchall()
            serial_number = []
            salesperson = []
            for value in result1:
                serial_number.append(value.get('serial_number', '') or '')
            for value in result2:
                salesperson.append(value.get('salesperson', '') or '')
            salesperson = list(set(salesperson))

        return [serial_number, salesperson]

    def get_product_ids(self, date_from, date_to, vendor_ids, categ_id=False):

        if vendor_ids:
            vendor_ids = vendor_ids
        else:
            vendor_ids = self.get_available_vendor_ids().ids

        vendor_ids_str = ','.join(str(x) for x in vendor_ids)
        vendor_ids = '(' + vendor_ids_str + ')'
        product_ids = []

        if categ_id:
            sql = ("""
    				select 
    					pp.id 
    				from product_product pp 
    					inner join product_template pt on (pp.product_tmpl_id = pt.id)
    					inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
    					inner join stock_move sm on (sm.product_id = pp.id)
    				where sm.date>='%s' and sm.date<='%s' and pt.categ_id=%s and
    					psi.partner_id in %s order by psi.product_code asc
    				""") % (date_from, date_to, categ_id, vendor_ids)
        else:
            sql = ("""
    						select 
    							pp.id 
    						from product_product pp 
    							inner join product_template pt on (pp.product_tmpl_id = pt.id)
    							inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
    							inner join stock_move sm on (sm.product_id = pp.id)
    						where sm.date>='%s' and sm.date<='%s' and psi.partner_id in %s order by psi.product_code asc
    						""") % (date_from, date_to, vendor_ids)

        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            if id[0] not in product_ids:
                product_ids += id
        return product_ids

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

    def get_sale_amount(self, date_from, date_to, product_id=None):

        sql = ("""
    		select 
    			SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) as net_qty
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
    			,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) end) as cost_price
    			,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END)* (1- sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) end)  as gross_margin
    			,count(*) as count_so
    		from sale_order_line sol
    			inner join sale_order so on (so.id = sol.order_id)
    			inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
    			inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    			inner join stock_move sm on (sp.id = sm.picking_id)
    			inner join product_product pp on (sol.product_id = pp.id)
    			inner join product_template pt on (pp.product_tmpl_id = pt.id)
    		where sp.date_done >= '%s' and sp.date_done <= '%s' 
    			and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id
    		""") % (date_from, date_to)

        if product_id:
            sql += ('and sol.product_id = %s' % (product_id))

        self._cr.execute(sql)

        result = self._cr.dictfetchall()

        retail_sale = 0
        invoice_sale = 0
        product_count = 0
        cost_price = 0
        count = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            count += value.get('count_so') or 0

        return [cost_price, invoice_sale, retail_sale, product_count, count]

    def get_sn_sp_of_so(self, date_from, date_to, product_id=None):
        if product_id:
            sql1 = ("""
    			select
    				spl.name as serial_number
    			from sale_order_line sol
    				inner join sale_order so on (so.id = sol.order_id)
    				inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
    				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    				inner join stock_move sm on (sp.id = sm.picking_id)
    				inner join stock_move_line sml on (sml.move_id = sm.id) 
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    			where sp.date_done >= '%s' and sp.date_done <= '%s' 
    				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id
    			""") % (date_from, date_to)
            sql1 += ('and sol.product_id = %s' % (product_id))
            sql2 = ("""
    			select
    				COALESCE(rp.short_code, rp.name) as salesperson
    			from sale_order_line sol
    				inner join sale_order so on (so.id = sol.order_id)
    				inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
    				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    				inner join stock_move sm on (sp.id = sm.picking_id)
    				inner join res_users ru on (ru.id = so.user_id)
    				inner join res_partner rp on (rp.id = ru.partner_id)
    			where sp.date_done >= '%s' and sp.date_done <= '%s' 
    				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id
    			""") % (date_from, date_to)
            sql2 += ('and sol.product_id = %s' % (product_id))
            self._cr.execute(sql1)
            result1 = self._cr.dictfetchall()
            self._cr.execute(sql2)
            result2 = self._cr.dictfetchall()
            serial_number = []
            salesperson = []
            for value in result1:
                serial_number.append(value.get('serial_number', '') or '')
            for value in result2:
                salesperson.append(value.get('salesperson', '') or '')
            salesperson = list(set(salesperson))

        return [serial_number, salesperson]

    def get_current_inventory_for_lot(self, product=None, lot=False):
        unit = 0
        product_cost_total = 0
        if lot:
            sql = ("""
    						select
    							coalesce(sum(svl.quantity), 0.00) as qty
    							,coalesce(sum(svl.value), 0.00) as cost_price_total
    							from stock_valuation_layer svl
    							inner join stock_move sm on(svl.stock_move_id = sm.id)
    							inner join stock_move_line sml on (sml.move_id = sm.id) 
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    						where
    							svl.product_id = %s and spl.name ='%s'
    						group by svl.product_id
    					""") % (product.id, lot)
        else:
            sql = ("""
    									select
    										coalesce(sum(svl.quantity), 0.00) as qty
    										,coalesce(sum(svl.value), 0.00) as cost_price_total
    										from stock_valuation_layer svl
    									where
    										svl.product_id = %s
    									group by svl.product_id
    								""") % (product.id)

        self._cr.execute(sql)

        result = self._cr.dictfetchall()
        for val in result:
            unit += val.get('qty', 0) or 0
            product_cost_total += val.get('cost_price_total', 0) or 0

        return [unit, product_cost_total]

    def get_dts_data_for_lot(self, period_date_from, period_date_to, product=None, lot=False):
        in_days = 0
        out_days = 0
        days = 0
        if lot:
            sql = ("""
    				select
    					sml.create_date as out_date
    					from stock_move_line sml
    					inner join stock_move sm on (sml.move_id = sm.id)
    					inner join stock_picking_type spt on (spt.id = sm.picking_type_id) 
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    						where  sml.state='done' and   spt.code in ('outgoing')
    						and sm.create_date BETWEEN '%s' and '%s' and sml.product_id = %s and spl.name ='%s'
    							order by sm.create_date ASC limit 1;
    			""") % (period_date_from, period_date_to, product.id, lot)
        else:
            sql = ("""
    							select
    								sml.create_date as out_date
    								from stock_valuation_layer sml
    								inner join stock_move sm on (sml.move_id = sm.id)
    								inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
    									where  sml.state='done' and   spt.code in ('outgoing')
    									and sm.create_date BETWEEN '%s' and '%s' and sml.product_id = %s
    										order by sm.create_date ASC limit 1;
    						""") % (period_date_from, period_date_to, product.id)

        self._cr.execute(sql)
        result = self._cr.dictfetchone()

        if result:
            out_days = result.get('out_date', 0) or 0
        date_to = period_date_to
        if out_days:
            date_to = out_days
        if lot:

            in_sql = ("""
                SELECT
                    sml.create_date AS in_date
                FROM
                    stock_move_line sml
                INNER JOIN
                    stock_move sm ON (sml.move_id = sm.id)
                INNER JOIN
                    stock_picking_type spt ON (spt.id = sm.picking_type_id)
                INNER JOIN
                    stock_lot spl ON (spl.id = sml.lot_id)  -- Add this JOIN clause
                WHERE
                    sml.state = 'done'
                    AND spt.code IN ('incoming', 'internal')
                    AND sm.create_date < '%s'
                    AND sml.product_id = %s
                    AND spl.name = '%s'
                ORDER BY
                    sm.create_date DESC
                LIMIT 1;
            """) % (date_to, product.id, lot)

        else:
            in_sql = ("""
                SELECT
                    sml.create_date AS in_date
                FROM
                    stock_move_line sml
                INNER JOIN
                    stock_move sm ON (sml.move_id = sm.id)
                INNER JOIN
                    stock_picking_type spt ON (spt.id = sm.picking_type_id)
                WHERE
                    sml.state = 'done'
                    AND spt.code IN ('incoming', 'internal')
                    AND sm.create_date < '%s'
                    AND sml.product_id = %s
                ORDER BY
                    sm.create_date DESC
                LIMIT 1;
            """) % (date_to, product.id)

        self._cr.execute(in_sql)

        in_result = self._cr.dictfetchone()

        if in_result:
            in_days = in_result.get('in_date', 0) or 0

        if out_days and in_days:
            days = (out_days - in_days).days
        if not days:
            days = 1

        return days

    def get_sale_amount_of_pos(self, date_from, date_to, product_id=None):
        sql = ("""
    		select 
    			SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) as net_qty
    			,sum(case when pt.list_price = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) end) as sale_price
    			,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) else ((pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END)* (100 - pol.discount))/100.0 end) as invoice_price 
    			,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) end) as cost_price
    			,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    					WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    					ELSE 0
    			   END) else ((pol.price_unit*sm.product_uom_qty)* (100 - pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin

    			,count(*) as count_so
    		from pos_order_line pol
    			inner join pos_order po on (po.id = pol.order_id)
    			inner join stock_picking sp on (sp.pos_order_id = po.id)
    			inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    			inner join stock_move sm on (sp.id = sm.picking_id)
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
        count = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            count += value.get('count_so') or 0

        return [cost_price, invoice_sale, retail_sale, product_count, count]

        # method of find DOH

    def get_day_on_hand(self, product=None):
        days = 0
        time = datetime.now()
        time = "'" + str(time) + "'"

        sql = ("""
    			select 
    				%s - create_date as time from stock_valuation_layer 
    				where product_id = %s and remaining_qty>0 
    				order by create_date ASC limit 1;
    		""") % (time, product.id)

        self._cr.execute(sql)

        result = self._cr.dictfetchall()
        for val in result:
            days = val.get('time', 0).days or 0

        return days

    def get_crm_shown(self, period_date_from, period_date_to, product=None):
        # count = 0
        # sql = ("""
        # 			select count(*) as number_of_record
        # 			from x_crm_lead_product_product_rel as crm_pro
        # 				inner join crm_lead cl on (cl.id = crm_pro.crm_lead_id)
        # 				where product_product_id = %s
        # 					and cl.create_date >= '%s'
        # 					and cl.create_date <= '%s';
        # 	""") % (product.id, period_date_from, period_date_to)
        #
        # self._cr.execute(sql)
        # result = self._cr.dictfetchall()
        #
        # for val in result:
        #     count += val.get('number_of_record', 0) or 0
        #
        return 10

    def get_sale_amount_for_lot(self, date_from, date_to, product_id=None, lot=False):
        if lot:
            sql = ("""
    			select 
    				SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) as net_qty
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
    				,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) end) as cost_price
    				,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END)* (1- sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) end)  as gross_margin
    				,count(*) as count_so
    			from sale_order_line sol
    				inner join sale_order so on (so.id = sol.order_id)
    				inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
    				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    				inner join stock_move sm on (sp.id = sm.picking_id)
    				inner join product_product pp on (sol.product_id = pp.id)
    				inner join product_template pt on (pp.product_tmpl_id = pt.id)
    				inner join stock_move_line sml on (sml.move_id = sm.id) 
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    			where sp.date_done >= '%s' and sp.date_done <= '%s' 
    				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id and spl.name='%s'
    			""") % (date_from, date_to, lot)
        else:
            sql = ("""
    						select 
    							SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) as net_qty
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
    							,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) end) as cost_price
    							,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END)* (1- sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) end)  as gross_margin
    							,count(*) as count_so
    						from sale_order_line sol
    							inner join sale_order so on (so.id = sol.order_id)
    							inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
    							inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    							inner join stock_move sm on (sp.id = sm.picking_id)
    							inner join product_product pp on (sol.product_id = pp.id)
    							inner join product_template pt on (pp.product_tmpl_id = pt.id)
    						where sp.date_done >= '%s' and sp.date_done <= '%s' 
    							and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id
    						""") % (date_from, date_to)
        if product_id:
            sql += ('and sol.product_id = %s' % (product_id))
        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        retail_sale = 0
        invoice_sale = 0
        product_count = 0
        cost_price = 0
        count = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            count += value.get('count_so') or 0

        return [cost_price, invoice_sale, retail_sale, product_count, count]

    def get_onhand_product_for_lot(self, product=None, lot_id=None, lot=False):
        available_qty = 0
        product_cost_amount = 0
        product_retail_amount = 0
        if lot:
            sql = ("""
    				select 
    					sq.quantity as qty
    					,sq.quantity* pp.std_price as cost_price
    					,sq.quantity* pt.list_price as sale_price
    					from stock_quant sq
    					INNER JOIN product_product pp on (pp.id = sq.product_id)
    					INNER JOIN stock_location sl on (sl.id=sq.location_id)
    					INNER JOIN product_template pt on (pp.product_tmpl_id = pt.id)
    					INNER JOIN stock_lot spl on (spl.id = sq.lot_id)
    					where sl.usage = 'internal' and spl.name ='%s'
    			""") % (lot)
        else:
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

    def get_onhand_product_history_for_lot(self, date_to, product_id=None, lot=False):
        available_qty = 0
        product_cost_amount_total = 0
        if lot:
            sql = ("""
    							select
    								coalesce(sum(svl.quantity), 0.00) as qty
    								,coalesce(sum(svl.value), 0.00) as cost_price_total
    								from stock_valuation_layer svl
    								inner join stock_move sm on(svl.stock_move_id = sm.id)
    								inner join stock_move_line sml on (sml.move_id = sm.id) 
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    							where
    								svl.product_id = %s and svl.create_date::DATE <= '%s' and spl.name = '%s'
    							group by svl.product_id
    						""") % (product_id, date_to, lot)

        else:
            sql = ("""
    				select
    					coalesce(sum(svl.quantity), 0.00) as qty
    					,coalesce(sum(svl.value), 0.00) as cost_price_total
    					from stock_valuation_layer svl
    				where
    					svl.product_id = %s and svl.create_date::DATE <= '%s'
    				group by svl.product_id
    			""") % (product_id, date_to)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        for val in result:
            available_qty += val.get('qty', 0) or 0
            product_cost_amount_total += val.get('cost_price_total', 0) or 0
        return [available_qty, product_cost_amount_total]

    def get_sale_amount_of_pos_for_lot(self, date_from, date_to, product_id=None, lot=False):
        if lot:
            sql = ("""
    			select 
    				SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) as net_qty
    				,sum(case when pt.list_price = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) end) as sale_price
    				,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) else ((pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END)* (100 - pol.discount))/100.0 end) as invoice_price 
    				,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) end) as cost_price
    				,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    						WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    						ELSE 0
    				   END) else ((pol.price_unit*sm.product_uom_qty)* (100 - pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin

    				,count(*) as count_so
    			from pos_order_line pol
    				inner join pos_order po on (po.id = pol.order_id)
    				inner join stock_picking sp on (sp.pos_order_id = po.id)
    				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    				inner join stock_move sm on (sp.id = sm.picking_id)
    				inner join product_product pp on (sm.product_id = pp.id)
    				inner join product_template pt on (pp.product_tmpl_id = pt.id)
    				inner join stock_move_line sml on (sml.move_id = sm.id) 
    				inner join stock_lot spl on (spl.id = sml.lot_id	)
    			where sp.date_done >= '%s' and sp.date_done <= '%s'
    				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = pol.product_id and spl.name = '%s'
    			""") % (date_from, date_to, lot)
        else:
            sql = ("""
    						select 
    							SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) as net_qty
    							,sum(case when pt.list_price = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) end) as sale_price
    							,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) else ((pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END)* (100 - pol.discount))/100.0 end) as invoice_price 
    							,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) end) as cost_price
    							,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
    									WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
    									ELSE 0
    							   END) else ((pol.price_unit*sm.product_uom_qty)* (100 - pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin

    							,count(*) as count_so
    						from pos_order_line pol
    							inner join pos_order po on (po.id = pol.order_id)
    							inner join stock_picking sp on (sp.pos_order_id = po.id)
    							inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
    							inner join stock_move sm on (sp.id = sm.picking_id)
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
        count = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            count += value.get('count_so') or 0
        return [cost_price, invoice_sale, retail_sale, product_count, count]

    def dollar_format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)

        # Convert value to a float or int
        try:
            value = float(value)
        except (ValueError, TypeError):
            # Handle the case where value is not a valid number
            return None  # You can return an appropriate value or raise an exception here

        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True).replace(r' ',
                                                                                         u'\N{NO-BREAK SPACE}').replace(
            r'-', u'\u2011')
        formatted_amount = "$ {}".format(formatted_amount[:formatted_amount.find('.')])
        return formatted_amount

    def get_current_inventory(self, product=None):
        unit = 0
        product_cost_total = 0
        sql = ("""
                    select
                        coalesce(sum(svl.quantity), 0.00) as qty
                        ,coalesce(sum(svl.value), 0.00) as cost_price_total
                        from stock_valuation_layer svl
                    where
                        svl.product_id = %s
                    group by svl.product_id
                """) % (product.id)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        for val in result:
            unit += val.get('qty', 0) or 0
            product_cost_total += val.get('cost_price_total', 0) or 0
        return [unit, product_cost_total]

    def get_dts_data(self, period_date_from, period_date_to, product=None):
        in_days = 0
        out_days = 0
        days = 0

        sql = ("""
    			select
    				sml.create_date as out_date
    				from stock_move_line sml
    				inner join stock_move sm on (sml.move_id = sm.id)
    				inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
    					where  sml.state='done' and spt.code in ('outgoing')
    					and sm.create_date BETWEEN '%s' and '%s' and sml.product_id = %s
    						order by sm.create_date ASC limit 1;
    		""") % (period_date_from, period_date_to, product.id)

        self._cr.execute(sql)
        result = self._cr.dictfetchone()

        if result:
            out_days = result.get('out_date', 0) or 0
        date_to = period_date_to
        if out_days:
            date_to = out_days
        in_sql = ("""
    					select
    						sml.create_date as in_date
    						from stock_move_line sml
    						inner join stock_move sm on (sml.move_id = sm.id)
    						inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
    							where  sml.state='done' and   spt.code in ('incoming','internal')
    							and sm.create_date < '%s' and sml.product_id = %s
    						order by sm.create_date DESC limit 1;
    				""") % (date_to, product.id)

        self._cr.execute(in_sql)
        in_result = self._cr.dictfetchone()

        if in_result:
            in_days = in_result.get('in_date', 0) or 0
        # if product.id == 80160:
        #     print(in_days, 'in_days')
        if out_days and in_days:
            days = (out_days - in_days).days
        if not days:
            days = 1

        return days

    def get_day_on_hand_for_lot(self, product=None, lot=False):
        days = 0
        time = datetime.now()
        time = "'" + str(time) + "'"
        if lot:
            sql = ("""
                SELECT 
                    %s - svl.create_date AS time 
                FROM 
                    stock_valuation_layer svl
                INNER JOIN 
                    stock_move sm ON (svl.stock_move_id = sm.id)
                WHERE 
                    svl.product_id = %s 
                    AND svl.remaining_qty > 0 
                ORDER BY 
                    svl.create_date ASC 
                LIMIT 1;
            """) % (time, product.id)
        else:
            sql = ("""
                SELECT 
                    %s - create_date AS time 
                FROM 
                    stock_valuation_layer 
                WHERE 
                    product_id = %s 
                    AND remaining_qty > 0 
                ORDER BY 
                    create_date ASC 
                LIMIT 1;
            """) % (time, product.id)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        for val in result:
            days = val.get('time', 0).days or 0
        return days

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        # total_values_cost = self.get_product_cost_total(options)
        sn_sp_all = self.get_sn_sp_all(options)
        all_parent_categ, all_categ = self.get_categ_all(options)
        context = self.env.context
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

        periods = options.get('comparison', False) and options.get('comparison', False).get('periods') or []
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        date_to_filter = context.get('date_to', False)
        if not date_to_filter:
            if options.get('date'):
                date_to_filter = options['date'].get('date_to') or options['date'].get('date')

        date_to_obj = datetime.strptime(date_to_filter, DEFAULT_SERVER_DATE_FORMAT).date()
        date_from_filter = context.get('date_from', False)
        if not date_from_filter:
            if options.get('date') and options['date'].get('date_from'):
                date_from_filter = options['date']['date_from']
        date_from_obj = datetime.strptime(date_from_filter, DEFAULT_SERVER_DATE_FORMAT).date()

        last_yr_date_to = date_to_obj - relativedelta(years=1)
        last_yr_date_from = date_from_obj - relativedelta(years=1)
        lly_date_to = date_to_obj - relativedelta(years=2)
        lly_date_from = date_from_obj - relativedelta(years=2)

        lines = []
        line_id = 0
        columns_main_header = [
            # {'name': _('TY'), 'class': 'border text-center', 'colspan': 16},
            {'name': _('LY'), 'class': 'border-left text-center', 'colspan': 2},
            {'name': _('LLY'), 'class': 'border-left text-center', 'colspan': 2},
            {'name': _('Inventory'), 'class': 'border-left text-center', 'colspan': 3},
        ]

        lines.append({
            'id': line_id,
            'name': _('TY'),
            'class': 'border text-center',
            'colspan': 18,
            'unfoldable': False,
            # 'class': 'o_account_reports_level1',
            'columns': columns_main_header,
            'title_hover': _('Header'),
            'level': 1
        })
        line_id += 1

        columns_header = [
            # {'name': _('Product Name'), 'class': 'number text-left'},
            {'name': _('Internal Reference'), 'class': 'text-left'},
            {'name': _('Serial Number'), 'class': 'number text-left'},
            {'name': _('O/M'), 'class': 'number text-left'},
            {'name': _('SP'), 'class': 'number text-left'},
            {'name': _('SThru%'), 'class': 'number text-right'},
            {'name': _('%Sales'), 'class': 'number text-right'},
            {'name': _('#'), 'class': 'number text-right'},
            {'name': _('Retail'), 'class': 'number text-right'},
            {'name': _('Sales'), 'class': 'number text-right'},
            {'name': _('COGS'), 'class': 'number text-right'},
            {'name': _('GM$'), 'class': 'number text-right'},
            {'name': _('GM%'), 'class': 'number text-right'},
            {'name': _('DTS'), 'class': 'number text-right'},
            {'name': _('GMROI'), 'class': 'number text-right'},
            {'name': _('TURN'), 'class': 'number text-right'},
            {'name': _('Shown'), 'class': 'number text-right'},
            {'name': _('#'), 'class': 'number text-right'},
            {'name': _('Sales'), 'class': 'number text-right'},
            {'name': _('#'), 'class': 'number text-right'},
            {'name': _('Sales'), 'class': 'number text-right'},
            {'name': _('#'), 'class': 'number text-right'},
            {'name': _('Cost'), 'class': 'number text-right'},
            {'name': _('DOH'), 'class': 'number text-right'},
        ]

        lines.append({
            'id': line_id,
            'name': _('Product Name'),
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': columns_header,
            'title_hover': _('Header'),
            # 'level': 1
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
        retail_sum = 0
        total_gmroi = 0
        total_turn = 0
        total_shown = 0
        total_period_oh = 0
        total_period_cogs = 0
        total_ly_units = 0
        total_ly_amnt = 0
        total_lly_units = 0
        total_lly_amnt = 0
        invt_unit = 0
        invt_cost = 0
        # invt_aged = 0
        invt_doh = 0
        total_dts = 0
        # initialize dictionary variable with zero based on periods
        periods = self.remove_duplicated_period(periods)

        for period in periods:
            period_date_from = period.get('date_from')
            invoice_sale_sum[period_date_from] = 0
            product_count_sum[period_date_from] = 0
            retail_sale_sum[period_date_from] = 0

        vendor_ids = options.get('partner_ids', [])

        for parent_categ in all_parent_categ:
            total_categ_dict = {int(parent_categ): {'categ_product_count': 0,
                                                    'categ_product_retail': 0,
                                                    'categ_product_sale_ly': 0,
                                                    'categ_product_sale_lly': 0,
                                                    'categ_product_invoice_amount': 0,
                                                    'categ_product_cost_amount': 0,
                                                    'categ_gross_margin': 0,
                                                    'categ_dts': 0,
                                                    'categ_gmroi': 0,
                                                    'categ_turn': 0,
                                                    'categ_shown': 0,
                                                    'categ_product_old_onhand_qty': 0,
                                                    'categ_product_old_onhand_cost': 0,
                                                    'categ_ly_product_product_count': 0,
                                                    'categ_lly_product_product_count': 0,
                                                    'categ_product_current_unit': 0,
                                                    'categ_product_current_cost': 0,
                                                    'categ_days_on_hand': 0
                                                    }}
            parent_categ = self.env['product.category'].browse(int(parent_categ))
            parent_categ_line_id = line_id
            line_id += 1
            product_ids = self.get_product_ids(date_from, date_to, vendor_ids, parent_categ.id)
            if product_ids:
                category_product_total = self.get_category_count_of_products(date_from, date_to,
                                                                             product_ids=product_ids)
                categ_product_count = 0
                categ_product_retail = 0
                categ_product_sale_ly = 0
                categ_product_sale_lly = 0
                categ_product_invoice_amount = 0
                categ_product_cost_amount = 0
                categ_gross_margin = 0
                categ_dts = 0
                categ_gmroi = 0
                categ_turn = 0
                categ_shown = 0
                categ_product_old_onhand_qty = 0
                categ_product_old_onhand_cost = 0
                categ_ly_product_product_count = 0
                categ_lly_product_product_count = 0
                categ_product_current_unit = 0
                categ_product_current_cost = 0
                categ_days_on_hand = 0
                for product in self.env['product.product'].browse(product_ids):
                    column = []
                    stop_current_execution = False

                    owner = self.get_product_owner(product_id=product.id)

                    if ownership in ['M', 'O']:
                        if ownership == 'M' and 'O' == owner:
                            continue
                        elif ownership == 'O' and 'M' == owner:
                            continue

                    def insert_newline(string, index, addin):
                        return string[:index] + addin + string[index:]

                    product_name = product.name[:50] or product.name
                    # quo = int(len(product.name) / 25) + 1
                    # for x in range(quo):
                    #     index = (x + 1) * 25 + x
                    #     product_name = insert_newline(product_name, index, '<br/>')
                    has_lots = False
                    for line in sn_sp_all:
                        if has_lots:
                            break
                        for key, val in line.items():
                            if key == product.id and len(val[0]) > 1:
                                has_lots = True
                                break
                    if not has_lots:
                        for period in periods:
                            period_date_from = period.get('date_from')
                            period_date_to = period.get('date_to')

                            product_sale_amount_list = self.get_sale_amount(period_date_from,
                                                                            period_date_to,
                                                                            product_id=product.id)
                            product_sale_amount_list_pos = self.get_sale_amount_of_pos(period_date_from,
                                                                                       period_date_to,
                                                                                       product_id=product.id)
                            product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                          product_sale_amount_list_pos[0]
                            product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                          product_sale_amount_list_pos[1]
                            product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                          product_sale_amount_list_pos[2]
                            product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                          product_sale_amount_list_pos[3]

                            product_cost_amount = product_sale_amount_list[0]
                            product_invoice_amount = product_sale_amount_list[1]
                            product_retail_sale = product_sale_amount_list[2]
                            product_product_count = product_sale_amount_list[3]
                            if not product_product_count:
                                stop_current_execution = True
                                break
                            categ_product_count += product_product_count

                            avg_count = product_sale_amount_list[4] + product_sale_amount_list_pos[4]

                            # last year data
                            ly_product_sale_amount_list = self.get_sale_amount(last_yr_date_from,
                                                                               last_yr_date_to,
                                                                               product_id=product.id)
                            ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(last_yr_date_from,
                                                                                          last_yr_date_to,
                                                                                          product_id=product.id)
                            ly_product_sale_amount_list[3] = ly_product_sale_amount_list[3] + \
                                                             ly_product_sale_amount_list_pos[3]

                            ly_product_product_count = ly_product_sale_amount_list[3]

                            # last last year data
                            lly_product_sale_amount_list = self.get_sale_amount(lly_date_from, lly_date_to,
                                                                                product_id=product.id)
                            lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(lly_date_from,
                                                                                           lly_date_to,
                                                                                           product_id=product.id)
                            lly_product_sale_amount_list[3] = lly_product_sale_amount_list[3] + \
                                                              lly_product_sale_amount_list_pos[3]

                            lly_product_product_count = lly_product_sale_amount_list[3]

                            product_onhand_product_history = self.get_onhand_product_history(period_date_to,
                                                                                             product_id=product.id)
                            product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history
                            # salesperson = self.get_salesperson(period_date_from, period_date_to,
                            #                                    product_id=product.id)

                            if period_date_from == date_from:
                                product_list = self.get_onhand_product(product=product)
                                onhand_product_cost_amount = product_list[2] or 0
                                sale_purchase_perc = 0
                                if category_product_total and product_product_count:
                                    sale_purchase_perc = product_product_count / (
                                        category_product_total)
                                sale_purchase_perc_sum += onhand_product_cost_amount
                                sale_purchase_perc = str(
                                    self.format_value(round(sale_purchase_perc * 100, 2))) + '%'

                                product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                product_sale_perc = str(
                                    self.format_value(round(product_perc * 100, 2))) + '%'
                                sale_perc_sum += product_perc
                                categ_product_retail += (product.lst_price * int(product_product_count))
                                column = [
                                    {'name': product.default_code and product.default_code or ''},
                                    {'name': '', 'class': 'text-left'},
                                    {'name': owner},
                                    {'name': ''},
                                    {'name': product_sale_perc},
                                    {'name': sale_purchase_perc},
                                    {'name': int(product_product_count)},
                                    {'name': self.dollar_format_value(product.lst_price * int(product_product_count))},

                                ]
                                retail_sum += (product.lst_price * int(product_product_count))

                            invoice_sale_sum[period_date_from] += product_invoice_amount
                            product_count_sum[period_date_from] += product_product_count
                            retail_sale_sum[period_date_from] += product_retail_sale
                            categ_product_invoice_amount += product_invoice_amount
                            product_invoice_amount_formatted = self.dollar_format_value(
                                product_invoice_amount)
                            product_discount = product_retail_sale and (
                                    product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                            product_discount_perc = str(
                                self.format_value(round(product_discount * 100, 2))) + '%'

                            if period_date_from == date_from:
                                average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                gross_margin = product_invoice_amount - product_cost_amount
                                gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                product_cost_sum += product_cost_amount
                                gross_margin_sum += gross_margin

                                product_cost_amount_dol = product_cost_amount
                                gross_margin_dol = gross_margin

                                categ_product_cost_amount += product_cost_amount
                                categ_gross_margin += gross_margin
                                gross_margin_perc = str(
                                    self.format_value(round(gross_margin_perc * 100, 2))) + '%'

                                current_inventory = self.get_current_inventory(product=product)
                                product_current_unit = current_inventory[0]
                                product_current_cost = current_inventory[1]
                                dts = self.get_dts_data(period_date_from, period_date_to, product=product)

                                # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                days_on_hand = self.get_day_on_hand(product=product)
                                shown = self.get_crm_shown(period_date_from, period_date_to,
                                                           product=product)
                                avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                column += [
                                    {'name': product_invoice_amount_formatted},
                                    {'name': self.dollar_format_value(product_cost_amount)},
                                    {'name': self.dollar_format_value(gross_margin)},
                                    {'name': gross_margin_perc},
                                    {'name': int(
                                        dts / product_product_count if product_product_count else 0)},
                                    {'name': self.format_value(
                                        gmroi / product_product_count if product_product_count else 0)},
                                    {'name': self.format_value(
                                        turn / product_product_count if product_product_count else 0)},
                                    {'name': int(shown)},
                                    {'name': int(ly_product_product_count), 'class': 'border-left number'},
                                    {'name': self.dollar_format_value(
                                        product.lst_price * ly_product_product_count)},
                                    {'name': int(lly_product_product_count), 'class': 'border-left number'},
                                    {'name': self.dollar_format_value(
                                        product.lst_price * lly_product_product_count)},
                                    {'name': int(product_current_unit), 'class': 'border-left number'},
                                    {'name': self.dollar_format_value(product_current_cost)},
                                    # {'name': self.format_value(aged_inventory) + '%'},
                                    {'name': int(
                                        days_on_hand / product_product_count if product_product_count else 0)},
                                ]
                                for line in sn_sp_all:
                                    for key, val in line.items():
                                        if key == product.id and len(val[0]) == 1 and len(val[1]) == 1:
                                            column[1].update({'name': val[0][0]})
                                            column[3].update({'name': val[1][0]})
                                        if key == product.id and len(val[1]) == 1:
                                            column[3].update({'name': val[1][0]})
                                        if key == product.id and len(val[1]) > 1 and not val[0]:
                                            column[3].update({'name': ",".join(val[1])})
                                        if key == product.id and len(val[1]) > 1 and val[0]:
                                            column[3].update({'name': ",".join(val[1])})

                                product_list = self.get_onhand_product(product=product)
                                product_available_qty = product_list[0]
                                product_available_product_price = product_list[1]
                                product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                product_available_qty_sum += product_available_qty
                                product_available_qty_perc_sum += product_available_qty_perc
                                product_available_product_price_sum += product_available_product_price
                                product_avg_on_hand_price_sum += product_avg_on_hand_price

                                total_gmroi += gmroi
                                categ_gmroi += gmroi
                                total_turn += turn
                                categ_turn += turn
                                total_shown += shown
                                categ_shown += shown
                                total_dts += dts
                                categ_dts += dts
                                total_period_oh += product_old_onhand_qty
                                categ_product_old_onhand_qty += product_old_onhand_qty
                                total_period_cogs += product_old_onhand_cost
                                categ_product_old_onhand_cost += product_old_onhand_cost
                                total_ly_units += ly_product_product_count
                                categ_ly_product_product_count += ly_product_product_count
                                categ_product_sale_ly += ly_product_product_count * product.lst_price
                                total_ly_amnt += (product.lst_price * ly_product_product_count)

                                total_lly_units += lly_product_product_count
                                categ_lly_product_product_count += lly_product_product_count
                                categ_product_sale_lly += product.lst_price * lly_product_product_count
                                total_lly_amnt += (product.lst_price * lly_product_product_count)

                                invt_unit += product_current_unit
                                invt_cost += product_current_cost
                                categ_product_current_unit += product_current_unit
                                categ_product_current_cost += product_current_cost
                                # invt_aged += aged_inventory
                                invt_doh += days_on_hand
                                categ_days_on_hand += days_on_hand
                                total_categ_dict.update({parent_categ.id:
                                    {
                                        # unsupported operand type(s) for +: 'float' and 'str'
                                        # 'categ_product_count':
                                        #  total_categ_dict[parent_categ.id][
                                        #      'categ_product_count'] + product_product_count,

                                        # 'categ_product_retail':
                                        #     total_categ_dict[parent_categ.id][
                                        #         'categ_product_retail'] + (
                                        #             product.lst_price * int(
                                        #         product_product_count)),
                                        'categ_product_sale_ly':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_sale_ly'] + (
                                                    ly_product_product_count * product.lst_price),
                                        'categ_product_sale_lly':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_sale_lly'] + (
                                                    product.lst_price * lly_product_product_count),
                                        'categ_product_invoice_amount':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_invoice_amount'] + product_invoice_amount,
                                        # 'categ_product_cost_amount':
                                        #     total_categ_dict[parent_categ.id][
                                        #         'categ_product_cost_amount'] + product_cost_amount,
                                        'categ_gross_margin':
                                            total_categ_dict[parent_categ.id][
                                                'categ_gross_margin'] + gross_margin,
                                        'categ_dts':
                                            total_categ_dict[parent_categ.id][
                                                'categ_dts'] + dts,
                                        'categ_gmroi':
                                            total_categ_dict[parent_categ.id][
                                                'categ_gmroi'] + gmroi,
                                        'categ_turn':
                                            total_categ_dict[parent_categ.id][
                                                'categ_turn'] + turn,
                                        'categ_shown':
                                            total_categ_dict[parent_categ.id][
                                                'categ_shown'] + shown,
                                        'categ_product_old_onhand_qty':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                        'categ_product_old_onhand_cost':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                        'categ_ly_product_product_count':
                                            total_categ_dict[parent_categ.id][
                                                'categ_ly_product_product_count'] + ly_product_product_count,
                                        'categ_lly_product_product_count':
                                            total_categ_dict[parent_categ.id][
                                                'categ_lly_product_product_count'] + lly_product_product_count,
                                        'categ_product_current_unit':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_current_unit'] + product_current_unit,
                                        'categ_product_current_cost':
                                            total_categ_dict[parent_categ.id][
                                                'categ_product_current_cost'] + product_current_cost,
                                        'categ_days_on_hand':
                                            total_categ_dict[parent_categ.id][
                                                'categ_days_on_hand'] + days_on_hand}})

                        if stop_current_execution:
                            continue

                        lines.append({
                            'id': line_id,
                            'name': product_name,
                            'unfoldable': False,
                            'class': 'vendor_int',
                            'columns': column,
                            'level': 3,

                        })

                        line_id += 1
                    else:
                        for line in sn_sp_all:
                            for key, val in line.items():
                                if key == product.id and len(val[0]) > 1:
                                    for data in val[0]:
                                        for period in periods:
                                            period_date_from = period.get('date_from')
                                            period_date_to = period.get('date_to')

                                            product_sale_amount_list = self.get_sale_amount_for_lot(
                                                period_date_from,
                                                period_date_to,
                                                product_id=product.id, lot=data)
                                            product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                period_date_from,
                                                period_date_to,
                                                product_id=product.id, lot=data)
                                            product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                          product_sale_amount_list_pos[0]
                                            product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                          product_sale_amount_list_pos[1]
                                            product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                          product_sale_amount_list_pos[2]
                                            product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                          product_sale_amount_list_pos[3]

                                            product_cost_amount = product_sale_amount_list[0]
                                            product_invoice_amount = product_sale_amount_list[1]
                                            product_retail_sale = product_sale_amount_list[2]
                                            product_product_count = product_sale_amount_list[3]
                                            if not product_product_count:
                                                stop_current_execution = True
                                                break
                                            categ_product_count += product_product_count

                                            avg_count = product_sale_amount_list[4] + \
                                                        product_sale_amount_list_pos[4]

                                            # last year data
                                            ly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                last_yr_date_from,
                                                last_yr_date_to,
                                                product_id=product.id, lot=data)
                                            ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                last_yr_date_from,
                                                last_yr_date_to,
                                                product_id=product.id, lot=data)
                                            ly_product_sale_amount_list[3] = ly_product_sale_amount_list[
                                                                                 3] + \
                                                                             ly_product_sale_amount_list_pos[
                                                                                 3]

                                            ly_product_product_count = ly_product_sale_amount_list[3]

                                            # last last year data
                                            lly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                lly_date_from, lly_date_to,
                                                product_id=product.id, lot=data)
                                            lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                lly_date_from,
                                                lly_date_to,
                                                product_id=product.id, lot=data)
                                            lly_product_sale_amount_list[3] = lly_product_sale_amount_list[
                                                                                  3] + \
                                                                              lly_product_sale_amount_list_pos[
                                                                                  3]

                                            lly_product_product_count = lly_product_sale_amount_list[3]

                                            product_onhand_product_history = self.get_onhand_product_history_for_lot(
                                                period_date_to,
                                                product_id=product.id, lot=data)
                                            product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history
                                            # salesperson = self.get_salesperson(period_date_from,
                                            #                                    period_date_to,
                                            #                                    product_id=product.id,
                                            #                                    lot=data)

                                            if period_date_from == date_from:

                                                product_list = self.get_onhand_product_for_lot(
                                                    product=product, lot=data)
                                                onhand_product_cost_amount = product_list[2] or 0
                                                sale_purchase_perc = 0
                                                if category_product_total and product_product_count:
                                                    sale_purchase_perc = product_product_count / (
                                                        category_product_total)
                                                sale_purchase_perc_sum += onhand_product_cost_amount
                                                sale_purchase_perc = str(
                                                    self.format_value(
                                                        round(sale_purchase_perc * 100, 2))) + '%'

                                                product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                                product_sale_perc = str(
                                                    self.format_value(round(product_perc * 100, 2))) + '%'
                                                sale_perc_sum += product_perc
                                                categ_product_retail += (product.lst_price * int(product_product_count))
                                                column = [
                                                    {'name': product.default_code and product.default_code or ''},
                                                    {'name': '', 'class': 'text-left'},
                                                    {'name': owner},
                                                    {'name': ''},
                                                    {'name': product_sale_perc},
                                                    {'name': sale_purchase_perc},
                                                    {'name': int(product_product_count)},
                                                    {'name': self.dollar_format_value(
                                                        product.lst_price * int(product_product_count))},

                                                ]
                                                retail_sum += (product.lst_price * int(product_product_count))

                                            invoice_sale_sum[period_date_from] += product_invoice_amount
                                            product_count_sum[period_date_from] += product_product_count
                                            retail_sale_sum[period_date_from] += product_retail_sale
                                            categ_product_invoice_amount += product_invoice_amount
                                            product_invoice_amount_formatted = self.dollar_format_value(
                                                product_invoice_amount)
                                            product_discount = product_retail_sale and (
                                                    product_retail_sale - product_invoice_amount) / product_retail_sale or 0

                                            if period_date_from == date_from:
                                                average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                                gross_margin = product_invoice_amount - product_cost_amount
                                                gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                                product_cost_sum += product_cost_amount
                                                gross_margin_sum += gross_margin

                                                product_cost_amount_dol = product_cost_amount
                                                gross_margin_dol = gross_margin

                                                average_sale = self.format_value(average_sale)
                                                categ_product_cost_amount += product_cost_amount
                                                product_cost_amount = self.dollar_format_value(
                                                    product_cost_amount)
                                                categ_gross_margin += gross_margin
                                                gross_margin_perc = str(
                                                    self.format_value(
                                                        round(gross_margin_perc * 100, 2))) + '%'

                                                current_inventory = self.get_current_inventory_for_lot(
                                                    product=product, lot=data)
                                                product_current_unit = current_inventory[0]
                                                product_current_cost = current_inventory[1]
                                                dts = self.get_dts_data_for_lot(period_date_from,
                                                                                period_date_to,
                                                                                product=product, lot=data)

                                                # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                                days_on_hand = self.get_day_on_hand_for_lot(product=product,
                                                                                            lot=data)
                                                shown = self.get_crm_shown(period_date_from, period_date_to,
                                                                           product=product)
                                                avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                                gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                                turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                                column += [
                                                    {'name': product_invoice_amount_formatted},
                                                    {'name': self.dollar_format_value(product_cost_amount)},
                                                    {'name': self.dollar_format_value(gross_margin)},
                                                    {'name': gross_margin_perc},
                                                    {'name': int(
                                                        dts / product_product_count if product_product_count else 0)},
                                                    {'name': self.format_value(
                                                        gmroi / product_product_count if product_product_count else 0)},
                                                    {'name': self.format_value(
                                                        turn / product_product_count if product_product_count else 0)},
                                                    {'name': int(shown)},
                                                    {'name': int(ly_product_product_count),
                                                     'class': 'border-left number'},
                                                    {'name': self.dollar_format_value(
                                                        product.lst_price * ly_product_product_count)},
                                                    {'name': int(lly_product_product_count),
                                                     'class': 'border-left number'},
                                                    {'name': self.dollar_format_value(
                                                        product.lst_price * lly_product_product_count)},
                                                    {'name': int(product_current_unit), 'class': 'border-left number'},
                                                    {'name': self.dollar_format_value(
                                                        product_current_cost)},
                                                    # {'name': self.format_value(aged_inventory) + '%'},
                                                    {'name': int(
                                                        days_on_hand / product_product_count if product_product_count else 0)},
                                                ]
                                                column[1].update({'name': data})
                                                if len(val[1]) == 1:
                                                    column[3].update({'name': val[1][0]})
                                                if len(val[1]) > 1:
                                                    column[3].update({'name': ",".join(val[1])})

                                                product_list = self.get_onhand_product_for_lot(
                                                    product=product, lot=data)
                                                product_available_qty = product_list[0]
                                                product_available_product_price = product_list[1]
                                                product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                                product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                                product_available_qty_sum += product_available_qty
                                                product_available_qty_perc_sum += product_available_qty_perc
                                                product_available_product_price_sum += product_available_product_price
                                                product_avg_on_hand_price_sum += product_avg_on_hand_price

                                                total_gmroi += gmroi
                                                categ_gmroi += gmroi
                                                total_turn += turn
                                                categ_turn += turn
                                                total_shown += shown
                                                categ_shown += shown
                                                total_dts += dts
                                                categ_dts += dts
                                                total_period_oh += product_old_onhand_qty
                                                categ_product_old_onhand_qty += product_old_onhand_qty
                                                total_period_cogs += product_old_onhand_cost
                                                categ_product_old_onhand_cost += product_old_onhand_cost
                                                total_ly_units += ly_product_product_count
                                                categ_ly_product_product_count += ly_product_product_count
                                                categ_product_sale_ly += ly_product_product_count * product.lst_price
                                                total_ly_amnt += (
                                                        product.lst_price * ly_product_product_count)

                                                total_lly_units += lly_product_product_count
                                                categ_lly_product_product_count += lly_product_product_count
                                                categ_product_sale_lly += product.lst_price * lly_product_product_count
                                                total_lly_amnt += (
                                                        product.lst_price * lly_product_product_count)

                                                invt_unit += product_current_unit
                                                invt_cost += product_current_cost
                                                categ_product_current_unit += product_current_unit
                                                categ_product_current_cost += product_current_cost
                                                # invt_aged += aged_inventory
                                                invt_doh += days_on_hand
                                                categ_days_on_hand += days_on_hand
                                                total_categ_dict.update({parent_categ.id:
                                                    {
                                                        #    KeyError: 'categ_product_count'
                                                        # 'categ_product_count':
                                                        #  total_categ_dict[parent_categ.id][
                                                        #      'categ_product_count'] + product_product_count,

                                                        # 'categ_product_retail':
                                                        #     total_categ_dict[parent_categ.id][
                                                        #         'categ_product_retail'] + (
                                                        #             product.lst_price * int(
                                                        #         product_product_count)),
                                                        'categ_product_sale_ly':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_sale_ly'] + (
                                                                    ly_product_product_count * product.lst_price),
                                                        'categ_product_sale_lly':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_sale_lly'] + (
                                                                    product.lst_price * lly_product_product_count),
                                                        'categ_product_invoice_amount':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_invoice_amount'] + product_invoice_amount,
                                                        # 'categ_product_cost_amount':
                                                        #     total_categ_dict[parent_categ.id][
                                                        #         'categ_product_cost_amount'] + product_cost_amount,
                                                        'categ_gross_margin':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_gross_margin'] + gross_margin,
                                                        'categ_dts':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_dts'] + dts,
                                                        'categ_gmroi':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_gmroi'] + gmroi,
                                                        'categ_turn':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_turn'] + turn,
                                                        'categ_shown':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_shown'] + shown,
                                                        'categ_product_old_onhand_qty':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                        'categ_product_old_onhand_cost':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                        'categ_ly_product_product_count':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_ly_product_product_count'] + ly_product_product_count,
                                                        'categ_lly_product_product_count':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_lly_product_product_count'] + lly_product_product_count,
                                                        'categ_product_current_unit':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_current_unit'] + product_current_unit,
                                                        'categ_product_current_cost':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_current_cost'] + product_current_cost,
                                                        'categ_days_on_hand':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_days_on_hand'] + days_on_hand}})

                                        if stop_current_execution:
                                            continue

                                        lines.append({
                                            'id': line_id,
                                            'name': product_name,
                                            'unfoldable': False,
                                            'class': 'vendor_int',
                                            'columns': column,
                                            'level': 3,

                                        })

                                        line_id += 1

            for sub_category in parent_categ.child_id:
                if str(sub_category.id) in all_categ:
                    category_level = 2
                    product_line_level = 3
                    total_categ_dict.update({sub_category.id: {'categ_product_count': 0,
                                                               'categ_product_retail': 0,
                                                               'categ_product_sale_ly': 0,
                                                               'categ_product_sale_lly': 0,
                                                               'categ_product_invoice_amount': 0,
                                                               'categ_product_cost_amount': 0,
                                                               'categ_gross_margin': 0,
                                                               'categ_dts': 0,
                                                               'categ_gmroi': 0,
                                                               'categ_turn': 0,
                                                               'categ_shown': 0,
                                                               'categ_product_old_onhand_qty': 0,
                                                               'categ_product_old_onhand_cost': 0,
                                                               'categ_ly_product_product_count': 0,
                                                               'categ_lly_product_product_count': 0,
                                                               'categ_product_current_unit': 0,
                                                               'categ_product_current_cost': 0,
                                                               'categ_days_on_hand': 0
                                                               }})
                    product_ids = self.get_product_ids(date_from, date_to, vendor_ids, sub_category.id)
                    if product_ids:
                        category_product_total = self.get_category_count_of_products(date_from, date_to,
                                                                                     product_ids=product_ids)
                        sub_category_line_id = line_id
                        line_id += 1
                        sub_category_level = category_level
                        for product in self.env['product.product'].browse(product_ids):
                            column = []
                            stop_current_execution = False

                            owner = self.get_product_owner(product_id=product.id)

                            if ownership in ['M', 'O']:
                                if ownership == 'M' and 'O' == owner:
                                    continue
                                elif ownership == 'O' and 'M' == owner:
                                    continue

                            def insert_newline(string, index, addin):
                                return string[:index] + addin + string[index:]

                            product_name = product.name[:50] or product.name
                            # quo = int(len(product.name) / 25) + 1
                            # for x in range(quo):
                            #     index = (x + 1) * 25 + x
                            #     product_name = insert_newline(product_name, index, '<br/>')
                            has_lots = False
                            for line in sn_sp_all:
                                if has_lots:
                                    break
                                for key, val in line.items():
                                    if key == product.id and len(val[0]) > 1:
                                        has_lots = True
                                        break
                            if not has_lots:
                                for period in periods:
                                    period_date_from = period.get('date_from')
                                    period_date_to = period.get('date_to')

                                    product_sale_amount_list = self.get_sale_amount(period_date_from,
                                                                                    period_date_to,
                                                                                    product_id=product.id)
                                    product_sale_amount_list_pos = self.get_sale_amount_of_pos(period_date_from,
                                                                                               period_date_to,
                                                                                               product_id=product.id)
                                    product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                  product_sale_amount_list_pos[0]
                                    product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                  product_sale_amount_list_pos[1]
                                    product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                  product_sale_amount_list_pos[2]
                                    product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                  product_sale_amount_list_pos[3]

                                    product_cost_amount = product_sale_amount_list[0]
                                    product_invoice_amount = product_sale_amount_list[1]
                                    product_retail_sale = product_sale_amount_list[2]
                                    product_product_count = product_sale_amount_list[3]
                                    if not product_product_count:
                                        stop_current_execution = True
                                        break

                                    avg_count = product_sale_amount_list[4] + product_sale_amount_list_pos[4]

                                    # last year data
                                    ly_product_sale_amount_list = self.get_sale_amount(last_yr_date_from,
                                                                                       last_yr_date_to,
                                                                                       product_id=product.id)
                                    ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(last_yr_date_from,
                                                                                                  last_yr_date_to,
                                                                                                  product_id=product.id)
                                    ly_product_sale_amount_list[3] = ly_product_sale_amount_list[3] + \
                                                                     ly_product_sale_amount_list_pos[3]

                                    ly_product_product_count = ly_product_sale_amount_list[3]

                                    # last last year data
                                    lly_product_sale_amount_list = self.get_sale_amount(lly_date_from, lly_date_to,
                                                                                        product_id=product.id)
                                    lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(lly_date_from,
                                                                                                   lly_date_to,
                                                                                                   product_id=product.id)
                                    lly_product_sale_amount_list[3] = lly_product_sale_amount_list[3] + \
                                                                      lly_product_sale_amount_list_pos[3]

                                    lly_product_product_count = lly_product_sale_amount_list[3]

                                    product_onhand_product_history = self.get_onhand_product_history(period_date_to,
                                                                                                     product_id=product.id)
                                    product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history

                                    if period_date_from == date_from:
                                        product_list = self.get_onhand_product(product=product)
                                        onhand_product_cost_amount = product_list[2] or 0
                                        sale_purchase_perc = 0
                                        if category_product_total and product_product_count:
                                            sale_purchase_perc = product_product_count / (
                                                category_product_total)
                                        sale_purchase_perc_sum += onhand_product_cost_amount
                                        sale_purchase_perc = str(
                                            self.format_value(round(sale_purchase_perc * 100, 2))) + '%'

                                        product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                        product_sale_perc = str(
                                            self.format_value(round(product_perc * 100, 2))) + '%'
                                        sale_perc_sum += product_perc
                                        column = [
                                            {'name': product.default_code and product.default_code or ''},
                                            {'name': '', 'class': 'text-left'},
                                            {'name': owner},
                                            {'name': ''},
                                            {'name': product_sale_perc},
                                            {'name': sale_purchase_perc},
                                            {'name': int(product_product_count)},
                                            {'name': self.dollar_format_value(
                                                product.lst_price * int(product_product_count))},
                                            # {'name': (self.format_value(product.lst_price)*product_product_count) },
                                            # {'name': product_cost_amount },
                                            # {'name': 0.0 },
                                            # {'name': 0.0 ,'style':'border-right:1px solid black;'},
                                            # {'name': self.format_value(product_old_onhand_qty)},
                                            # {'name': self.format_value(product_old_onhand_cost),'style':'border-right:1px solid black;'},
                                            # {'name': self.format_value(ly_product_product_count) },
                                            # {'name': self.format_value(product.lst_price * ly_product_product_count) ,'style':'border-right:1px solid black;'},
                                            # {'name': self.format_value(lly_product_product_count) },
                                            # {'name': self.format_value(product.lst_price * lly_product_product_count) ,'style':'border-right:1px solid black;'},
                                            # {'name': 0.0 },
                                            # {'name': 0.0 },
                                            # {'name': 0.0 },
                                            # {'name': 0.0 },
                                            # {'name':owner},
                                            # {'name':product_name},
                                            # {'name':self.get_vendor_reference(product)},
                                            # {'name':self.format_value(product.lst_price)},
                                            # {'name':product_product_count},
                                            # {'name':product_sale_perc},
                                            # {'name':sale_purchase_perc},
                                            # {'name':'0.00'}
                                        ]
                                        retail_sum += (product.lst_price * int(product_product_count))

                                    invoice_sale_sum[period_date_from] += product_invoice_amount
                                    product_count_sum[period_date_from] += product_product_count
                                    retail_sale_sum[period_date_from] += product_retail_sale
                                    product_invoice_amount_formatted = self.dollar_format_value(
                                        product_invoice_amount)
                                    product_discount = product_retail_sale and (
                                            product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                    # column += [
                                    # 	{'name':product_invoice_amount_formatted},
                                    # 	{'name':product_discount_perc}
                                    # 	]
                                    if period_date_from == date_from:
                                        average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                        gross_margin = product_invoice_amount - product_cost_amount
                                        gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                        product_cost_sum += product_cost_amount
                                        gross_margin_sum += gross_margin

                                        product_cost_amount_dol = product_cost_amount
                                        gross_margin_dol = gross_margin

                                        gross_margin_perc = str(
                                            self.format_value(round(gross_margin_perc * 100, 2))) + '%'

                                        current_inventory = self.get_current_inventory(product=product)
                                        product_current_unit = current_inventory[0]
                                        product_current_cost = current_inventory[1]
                                        dts = self.get_dts_data(period_date_from, period_date_to, product=product)

                                        # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                        days_on_hand = self.get_day_on_hand(product=product)
                                        shown = self.get_crm_shown(period_date_from, period_date_to,
                                                                   product=product)
                                        avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                        gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                        turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                        column += [
                                            {'name': product_invoice_amount_formatted},
                                            {'name': self.dollar_format_value(product_cost_amount)},
                                            {'name': self.dollar_format_value(gross_margin)},
                                            {'name': gross_margin_perc},
                                            {'name': int(
                                                dts / product_product_count if product_product_count else 0)},
                                            {'name': self.format_value(
                                                gmroi / product_product_count if product_product_count else 0)},
                                            {'name': self.format_value(
                                                turn / product_product_count if product_product_count else 0)},
                                            {'name': int(shown)},
                                            {'name': int(ly_product_product_count), 'class': 'border-left number'},
                                            {'name': self.dollar_format_value(
                                                product.lst_price * ly_product_product_count)},
                                            {'name': int(lly_product_product_count), 'class': 'border-left number'},
                                            {'name': self.dollar_format_value(
                                                product.lst_price * lly_product_product_count)},
                                            {'name': int(product_current_unit), 'class': 'border-left number'},
                                            {'name': self.dollar_format_value(product_current_cost)},
                                            # {'name': self.format_value(aged_inventory) + '%'},
                                            {'name': int(
                                                days_on_hand / product_product_count if product_product_count else 0)},
                                        ]
                                        for line in sn_sp_all:
                                            for key, val in line.items():
                                                if key == product.id and len(val[0]) == 1 and len(val[1]) == 1:
                                                    column[1].update({'name': val[0][0]})
                                                    column[3].update({'name': val[1][0]})
                                                if key == product.id and len(val[1]) == 1:
                                                    column[3].update({'name': val[1][0]})
                                                if key == product.id and len(val[1]) > 1 and not val[0]:
                                                    column[3].update({'name': ",".join(val[1])})
                                                if key == product.id and len(val[1]) > 1 and val[0]:
                                                    column[3].update({'name': ",".join(val[1])})

                                        product_list = self.get_onhand_product(product=product)
                                        product_available_qty = product_list[0]
                                        product_available_product_price = product_list[1]
                                        product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                        product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                        product_available_qty_sum += product_available_qty
                                        product_available_qty_perc_sum += product_available_qty_perc
                                        product_available_product_price_sum += product_available_product_price
                                        product_avg_on_hand_price_sum += product_avg_on_hand_price

                                        total_gmroi += gmroi
                                        total_turn += turn
                                        total_shown += shown
                                        total_dts += dts
                                        total_period_oh += product_old_onhand_qty
                                        total_period_cogs += product_old_onhand_cost
                                        total_ly_units += ly_product_product_count
                                        total_ly_amnt += (product.lst_price * ly_product_product_count)

                                        total_lly_units += lly_product_product_count
                                        total_lly_amnt += (product.lst_price * lly_product_product_count)

                                        invt_unit += product_current_unit
                                        invt_cost += product_current_cost
                                        # invt_aged += aged_inventory
                                        invt_doh += days_on_hand
                                        total_categ_dict.update({sub_category.id:
                                                                     {'categ_product_count':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_count'] + product_product_count,
                                                                      'categ_product_retail':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_retail'] + (
                                                                                  product.lst_price * int(
                                                                              product_product_count)),
                                                                      'categ_product_sale_ly':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_sale_ly'] + (
                                                                                  ly_product_product_count * product.lst_price),
                                                                      'categ_product_sale_lly':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_sale_lly'] + (
                                                                                  product.lst_price * lly_product_product_count),
                                                                      'categ_product_invoice_amount':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_invoice_amount'] + product_invoice_amount,
                                                                      'categ_product_cost_amount':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_cost_amount'] + product_cost_amount,
                                                                      'categ_gross_margin':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_gross_margin'] + gross_margin,
                                                                      'categ_dts': total_categ_dict[sub_category.id][
                                                                                       'categ_dts'] + dts,
                                                                      'categ_gmroi': total_categ_dict[sub_category.id][
                                                                                         'categ_gmroi'] + gmroi,
                                                                      'categ_turn': total_categ_dict[sub_category.id][
                                                                                        'categ_turn'] + turn,
                                                                      'categ_shown': total_categ_dict[sub_category.id][
                                                                                         'categ_shown'] + shown,
                                                                      'categ_product_old_onhand_qty':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                      'categ_product_old_onhand_cost':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                      'categ_ly_product_product_count':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_ly_product_product_count'] + ly_product_product_count,
                                                                      'categ_lly_product_product_count':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_lly_product_product_count'] + lly_product_product_count,
                                                                      'categ_product_current_unit':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_current_unit'] + product_current_unit,
                                                                      'categ_product_current_cost':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_product_current_cost'] + product_current_cost,
                                                                      'categ_days_on_hand':
                                                                          total_categ_dict[sub_category.id][
                                                                              'categ_days_on_hand'] + days_on_hand}})
                                        total_categ_dict.update({parent_categ.id:
                                            {
                                                # 'categ_product_count':
                                                #  total_categ_dict[parent_categ.id][
                                                #      'categ_product_count'] + product_product_count,
                                                # 'categ_product_retail':
                                                # total_categ_dict[parent_categ.id][
                                                #     'categ_product_retail'] + (
                                                #         product.lst_price * int(
                                                #     product_product_count)),
                                                'categ_product_sale_ly':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_sale_ly'] + (
                                                            ly_product_product_count * product.lst_price),
                                                'categ_product_sale_lly':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_sale_lly'] + (
                                                            product.lst_price * lly_product_product_count),
                                                'categ_product_invoice_amount':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_invoice_amount'] + product_invoice_amount,
                                                # 'categ_product_cost_amount':
                                                #     total_categ_dict[parent_categ.id][
                                                #         'categ_product_cost_amount'] + product_cost_amount,
                                                'categ_gross_margin':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_gross_margin'] + gross_margin,
                                                'categ_dts': total_categ_dict[parent_categ.id][
                                                                 'categ_dts'] + dts,
                                                'categ_gmroi': total_categ_dict[parent_categ.id][
                                                                   'categ_gmroi'] + gmroi,
                                                'categ_turn': total_categ_dict[parent_categ.id][
                                                                  'categ_turn'] + turn,
                                                'categ_shown': total_categ_dict[parent_categ.id][
                                                                   'categ_shown'] + shown,
                                                'categ_product_old_onhand_qty':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                'categ_product_old_onhand_cost':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                'categ_ly_product_product_count':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_ly_product_product_count'] + ly_product_product_count,
                                                'categ_lly_product_product_count':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_lly_product_product_count'] + lly_product_product_count,
                                                'categ_product_current_unit':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_current_unit'] + product_current_unit,
                                                'categ_product_current_cost':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_product_current_cost'] + product_current_cost,
                                                'categ_days_on_hand':
                                                    total_categ_dict[parent_categ.id][
                                                        'categ_days_on_hand'] + days_on_hand}})

                                if stop_current_execution:
                                    continue

                                lines.append({
                                    'id': line_id,
                                    'name': product_name,
                                    'unfoldable': False,
                                    'class': 'vendor_int',
                                    'columns': column,
                                    'level': product_line_level,

                                })

                                line_id += 1
                            else:
                                for line in sn_sp_all:
                                    for key, val in line.items():
                                        if key == product.id and len(val[0]) > 1:
                                            for data in val[0]:
                                                for period in periods:
                                                    period_date_from = period.get('date_from')
                                                    period_date_to = period.get('date_to')

                                                    product_sale_amount_list = self.get_sale_amount_for_lot(
                                                        period_date_from,
                                                        period_date_to,
                                                        product_id=product.id, lot=data)
                                                    product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                        period_date_from,
                                                        period_date_to,
                                                        product_id=product.id, lot=data)
                                                    product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                                  product_sale_amount_list_pos[0]
                                                    product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                                  product_sale_amount_list_pos[1]
                                                    product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                                  product_sale_amount_list_pos[2]
                                                    product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                                  product_sale_amount_list_pos[3]

                                                    product_cost_amount = product_sale_amount_list[0]
                                                    product_invoice_amount = product_sale_amount_list[1]
                                                    product_retail_sale = product_sale_amount_list[2]
                                                    product_product_count = product_sale_amount_list[3]
                                                    if not product_product_count:
                                                        stop_current_execution = True
                                                        break

                                                    avg_count = product_sale_amount_list[4] + \
                                                                product_sale_amount_list_pos[4]

                                                    # last year data
                                                    ly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                        last_yr_date_from,
                                                        last_yr_date_to,
                                                        product_id=product.id, lot=data)
                                                    ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                        last_yr_date_from,
                                                        last_yr_date_to,
                                                        product_id=product.id, lot=data)
                                                    ly_product_sale_amount_list[3] = ly_product_sale_amount_list[
                                                                                         3] + \
                                                                                     ly_product_sale_amount_list_pos[
                                                                                         3]

                                                    ly_product_product_count = ly_product_sale_amount_list[3]

                                                    # last last year data
                                                    lly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                        lly_date_from, lly_date_to,
                                                        product_id=product.id, lot=data)
                                                    lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                        lly_date_from,
                                                        lly_date_to,
                                                        product_id=product.id, lot=data)
                                                    lly_product_sale_amount_list[3] = lly_product_sale_amount_list[
                                                                                          3] + \
                                                                                      lly_product_sale_amount_list_pos[
                                                                                          3]

                                                    lly_product_product_count = lly_product_sale_amount_list[3]

                                                    product_onhand_product_history = self.get_onhand_product_history_for_lot(
                                                        period_date_to,
                                                        product_id=product.id, lot=data)
                                                    product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history

                                                    if period_date_from == date_from:
                                                        product_list = self.get_onhand_product_for_lot(
                                                            product=product, lot=data)
                                                        onhand_product_cost_amount = product_list[2] or 0
                                                        sale_purchase_perc = 0
                                                        if category_product_total and product_product_count:
                                                            sale_purchase_perc = product_product_count / (
                                                                category_product_total)
                                                        sale_purchase_perc_sum += onhand_product_cost_amount
                                                        sale_purchase_perc = str(
                                                            self.format_value(
                                                                round(sale_purchase_perc * 100, 2))) + '%'

                                                        product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                                        product_sale_perc = str(
                                                            self.format_value(round(product_perc * 100, 2))) + '%'
                                                        sale_perc_sum += product_perc
                                                        column = [
                                                            {
                                                                'name': product.default_code and product.default_code or ''},
                                                            {'name': '', 'class': 'text-left'},
                                                            {'name': owner},
                                                            {'name': ''},
                                                            {'name': product_sale_perc},
                                                            {'name': sale_purchase_perc},
                                                            {'name': int(product_product_count)},
                                                            {'name': self.dollar_format_value(
                                                                product.lst_price * int(product_product_count))},
                                                            # {'name': (self.format_value(product.lst_price)*product_product_count) },
                                                            # {'name': product_cost_amount },
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 ,'style':'border-right:1px solid black;'},
                                                            # {'name': self.format_value(product_old_onhand_qty)},
                                                            # {'name': self.format_value(product_old_onhand_cost),'style':'border-right:1px solid black;'},
                                                            # {'name': self.format_value(ly_product_product_count) },
                                                            # {'name': self.format_value(product.lst_price * ly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                            # {'name': self.format_value(lly_product_product_count) },
                                                            # {'name': self.format_value(product.lst_price * lly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 },
                                                            # {'name':owner},
                                                            # {'name':product_name},
                                                            # {'name':self.get_vendor_reference(product)},
                                                            # {'name':self.format_value(product.lst_price)},
                                                            # {'name':product_product_count},
                                                            # {'name':product_sale_perc},
                                                            # {'name':sale_purchase_perc},
                                                            # {'name':'0.00'}
                                                        ]
                                                        retail_sum += (product.lst_price * int(product_product_count))

                                                    invoice_sale_sum[period_date_from] += product_invoice_amount
                                                    product_count_sum[period_date_from] += product_product_count
                                                    retail_sale_sum[period_date_from] += product_retail_sale
                                                    product_invoice_amount_formatted = self.dollar_format_value(
                                                        product_invoice_amount)
                                                    product_discount = product_retail_sale and (
                                                            product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                                    # column += [
                                                    # 	{'name':product_invoice_amount_formatted},
                                                    # 	{'name':product_discount_perc}
                                                    # 	]
                                                    if period_date_from == date_from:
                                                        average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                                        gross_margin = product_invoice_amount - product_cost_amount
                                                        gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                                        product_cost_sum += product_cost_amount
                                                        gross_margin_sum += gross_margin

                                                        product_cost_amount_dol = product_cost_amount
                                                        gross_margin_dol = gross_margin

                                                        gross_margin_perc = str(
                                                            self.format_value(
                                                                round(gross_margin_perc * 100, 2))) + '%'

                                                        current_inventory = self.get_current_inventory_for_lot(
                                                            product=product, lot=data)
                                                        product_current_unit = current_inventory[0]
                                                        product_current_cost = current_inventory[1]
                                                        dts = self.get_dts_data_for_lot(period_date_from,
                                                                                        period_date_to,
                                                                                        product=product, lot=data)

                                                        # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                                        days_on_hand = self.get_day_on_hand_for_lot(product=product,
                                                                                                    lot=data)
                                                        shown = self.get_crm_shown(period_date_from, period_date_to,
                                                                                   product=product)
                                                        avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                                        gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                                        turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                                        column += [
                                                            {'name': product_invoice_amount_formatted},
                                                            {'name': self.dollar_format_value(product_cost_amount)},
                                                            {'name': self.dollar_format_value(gross_margin)},
                                                            {'name': gross_margin_perc},
                                                            {'name': int(
                                                                dts / product_product_count if product_product_count else 0)},
                                                            {'name': self.format_value(
                                                                gmroi / product_product_count if product_product_count else 0)},
                                                            {'name': self.format_value(
                                                                turn / product_product_count if product_product_count else 0)},
                                                            {'name': int(shown)},
                                                            {'name': int(ly_product_product_count),
                                                             'class': 'border-left number'},
                                                            {'name': self.dollar_format_value(
                                                                product.lst_price * ly_product_product_count)},
                                                            {'name': int(lly_product_product_count),
                                                             'class': 'border-left number'},
                                                            {'name': self.dollar_format_value(
                                                                product.lst_price * lly_product_product_count)},
                                                            {'name': int(product_current_unit),
                                                             'class': 'border-left number'},
                                                            {'name': self.dollar_format_value(
                                                                product_current_cost)},
                                                            # {'name': self.format_value(aged_inventory) + '%'},
                                                            {'name': int(
                                                                days_on_hand / product_product_count if product_product_count else 0)},
                                                        ]

                                                        if len(val[1]) == 1:
                                                            column[3].update({'name': val[1][0]})
                                                        if len(val[1]) > 1:
                                                            column[3].update({'name': ",".join(val[1])})
                                                        column[1].update({'name': data})
                                                        # for line in sn_sp_all[0]:
                                                        # 	for key, val in line.items():
                                                        # 		if key == product.id and len(val)==1:
                                                        # 			column[1].update({'name': val[0]})
                                                        # for line in sn_sp_all[1]:
                                                        # 	for key, val in line.items():
                                                        # 		if key == product.id and len(val)==1:
                                                        # 			column[3].update({'name': val[0]})

                                                        product_list = self.get_onhand_product_for_lot(
                                                            product=product, lot=data)
                                                        product_available_qty = product_list[0]
                                                        product_available_product_price = product_list[1]
                                                        product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                                        product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                                        product_available_qty_sum += product_available_qty
                                                        product_available_qty_perc_sum += product_available_qty_perc
                                                        product_available_product_price_sum += product_available_product_price
                                                        product_avg_on_hand_price_sum += product_avg_on_hand_price

                                                        total_gmroi += gmroi
                                                        total_turn += turn
                                                        total_shown += shown
                                                        total_dts += dts
                                                        total_period_oh += product_old_onhand_qty
                                                        total_period_cogs += product_old_onhand_cost
                                                        total_ly_units += ly_product_product_count
                                                        total_ly_amnt += (
                                                                product.lst_price * ly_product_product_count)

                                                        total_lly_units += lly_product_product_count
                                                        total_lly_amnt += (
                                                                product.lst_price * lly_product_product_count)

                                                        invt_unit += product_current_unit
                                                        invt_cost += product_current_cost
                                                        # invt_aged += aged_inventory
                                                        invt_doh += days_on_hand
                                                        total_categ_dict.update({sub_category.id:
                                                                                     {'categ_product_count':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_count'] + product_product_count,
                                                                                      'categ_product_retail':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_retail'] + (
                                                                                                  product.lst_price * int(
                                                                                              product_product_count)),
                                                                                      'categ_product_sale_ly':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_sale_ly'] + (
                                                                                                  ly_product_product_count * product.lst_price),
                                                                                      'categ_product_sale_lly':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_sale_lly'] + (
                                                                                                  product.lst_price * lly_product_product_count),
                                                                                      'categ_product_invoice_amount':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                      'categ_product_cost_amount':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_cost_amount'] + product_cost_amount,
                                                                                      'categ_gross_margin':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_gross_margin'] + gross_margin,
                                                                                      'categ_dts':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_dts'] + dts,
                                                                                      'categ_gmroi':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_gmroi'] + gmroi,
                                                                                      'categ_turn':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_turn'] + turn,
                                                                                      'categ_shown':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_shown'] + shown,
                                                                                      'categ_product_old_onhand_qty':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                      'categ_product_old_onhand_cost':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                      'categ_ly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                      'categ_lly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                      'categ_product_current_unit':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_current_unit'] + product_current_unit,
                                                                                      'categ_product_current_cost':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_current_cost'] + product_current_cost,
                                                                                      'categ_days_on_hand':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                        
                                                                                              'categ_days_on_hand'] + days_on_hand}})
                                                        print("parent_categ",parent_categ)
                                                        print("SDFsdfsdfsdfsd",total_categ_dict[parent_categ.id])
                                                        total_categ_dict.update({parent_categ.id:
                                                                                    {'categ_product_count':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_count'] + product_product_count  if 'categ_product_count' in  total_categ_dict[
                                                                                              parent_categ.id] else 0,
                                                                                      'categ_product_retail':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_retail'] + (
                                                                                                  product.lst_price * int(
                                                                                              product_product_count)) if 'categ_product_retail' in total_categ_dict[
                                                                                              parent_categ.id] else   0,
                                                                                      'categ_product_sale_ly':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_sale_ly'] + (
                                                                                                  ly_product_product_count * product.lst_price),
                                                                                      'categ_product_sale_lly':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_sale_lly'] + (
                                                                                                  product.lst_price * lly_product_product_count),
                                                                                      'categ_product_invoice_amount':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                      'categ_product_cost_amount':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_cost_amount'] + product_cost_amount if 'categ_product_cost_amount' in total_categ_dict[
                                                                                              parent_categ.id] else 0 ,
                                                                                      'categ_gross_margin':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_gross_margin'] + gross_margin,
                                                                                      'categ_dts':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_dts'] + dts,
                                                                                      'categ_gmroi':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_gmroi'] + gmroi,
                                                                                      'categ_turn':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_turn'] + turn,
                                                                                      'categ_shown':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_shown'] + shown,
                                                                                      'categ_product_old_onhand_qty':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                      'categ_product_old_onhand_cost':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                      'categ_ly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                      'categ_lly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                      'categ_product_current_unit':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_current_unit'] + product_current_unit,
                                                                                      'categ_product_current_cost':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_product_current_cost'] + product_current_cost,
                                                                                      'categ_days_on_hand':
                                                                                          total_categ_dict[
                                                                                              parent_categ.id][
                                                                                              'categ_days_on_hand'] + days_on_hand}})

                                                if stop_current_execution:
                                                    continue

                                                lines.append({
                                                    'id': line_id,
                                                    'name': product_name,
                                                    'unfoldable': False,
                                                    'class': 'vendor_int',
                                                    'columns': column,
                                                    'level': product_line_level,

                                                })

                                                line_id += 1
                        categ_gross_margin_perc = total_categ_dict[sub_category.id]['categ_product_invoice_amount'] and \
                                                  total_categ_dict[sub_category.id]['categ_gross_margin'] / \
                                                  total_categ_dict[sub_category.id]['categ_product_invoice_amount'] or 0
                        categ_column = [
                            {'name': ''},
                            {'name': ''},
                            {'name': ''},
                            {'name': ''},
                            {'name': ''},
                            {'name': ''},
                            {'name': int(total_categ_dict[sub_category.id]['categ_product_count'])},
                            {'name': self.dollar_format_value(
                                total_categ_dict[sub_category.id]['categ_product_retail'])},
                            {'name': self.dollar_format_value(
                                total_categ_dict[sub_category.id]['categ_product_invoice_amount'])},
                            {'name': self.dollar_format_value(
                                total_categ_dict[sub_category.id]['categ_product_cost_amount'])},
                            {'name': self.dollar_format_value(total_categ_dict[sub_category.id]['categ_gross_margin'])},
                            {'name': str(self.format_value(round(categ_gross_margin_perc * 100, 2))) + '%'},
                            {'name': int(
                                total_categ_dict[sub_category.id]['categ_dts'] / total_categ_dict[sub_category.id][
                                    'categ_product_count'] if total_categ_dict[sub_category.id][
                                    'categ_product_count'] else 0)},
                            {'name': self.format_value(
                                total_categ_dict[sub_category.id]['categ_gmroi'] / total_categ_dict[sub_category.id][
                                    'categ_product_count'] if total_categ_dict[sub_category.id][
                                    'categ_product_count'] else 0)},
                            {'name': self.format_value(
                                total_categ_dict[sub_category.id]['categ_turn'] / total_categ_dict[sub_category.id][
                                    'categ_product_count'] if total_categ_dict[sub_category.id][
                                    'categ_product_count'] else 0)},
                            {'name': int(total_categ_dict[sub_category.id]['categ_shown'])},
                            {'name': int(total_categ_dict[sub_category.id]['categ_ly_product_product_count']),
                             'class': 'border-left  number'},
                            {'name': self.dollar_format_value(
                                total_categ_dict[sub_category.id]['categ_product_sale_ly'])},

                            {'name': int(total_categ_dict[sub_category.id]['categ_lly_product_product_count']),
                             'class': 'border-left  number'},
                            {'name': self.dollar_format_value(
                                total_categ_dict[sub_category.id]['categ_product_sale_lly'])},
                            {'name': int(total_categ_dict[sub_category.id]['categ_product_current_unit']),
                             'class': 'border-left  number'},
                            {'name': self.dollar_format_value(
                                total_categ_dict[sub_category.id]['categ_product_current_cost'])},
                            {'name': int(
                                total_categ_dict[sub_category.id]['categ_days_on_hand'] /
                                total_categ_dict[sub_category.id][
                                    'categ_product_count'] if total_categ_dict[sub_category.id][
                                    'categ_product_count'] else 0)}, ]
                        lines.append({
                            'id': sub_category_line_id,
                            'name': sub_category.complete_name,
                            'unfoldable': False,
                            'class': 'o_account_reports_level1',
                            'title_hover': _('category'),
                            'level': sub_category_level,
                            'columns': categ_column,
                        })
                    for category in sub_category.child_id:
                        if str(category.id) in all_categ:
                            category_level = 3
                            product_line_level = 4
                            category_total_level = 3
                            total_categ_dict.update({category.id: {'categ_product_count': 0,
                                                                   'categ_product_retail': 0,
                                                                   'categ_product_sale_ly': 0,
                                                                   'categ_product_sale_lly': 0,
                                                                   'categ_product_invoice_amount': 0,
                                                                   'categ_product_cost_amount': 0,
                                                                   'categ_gross_margin': 0,
                                                                   'categ_dts': 0,
                                                                   'categ_gmroi': 0,
                                                                   'categ_turn': 0,
                                                                   'categ_shown': 0,
                                                                   'categ_product_old_onhand_qty': 0,
                                                                   'categ_product_old_onhand_cost': 0,
                                                                   'categ_ly_product_product_count': 0,
                                                                   'categ_lly_product_product_count': 0,
                                                                   'categ_product_current_unit': 0,
                                                                   'categ_product_current_cost': 0,
                                                                   'categ_days_on_hand': 0
                                                                   }})
                            product_ids = self.get_product_ids(date_from, date_to, vendor_ids, category.id)
                            if product_ids:
                                category_product_total = self.get_category_count_of_products(date_from, date_to,
                                                                                             product_ids=product_ids)
                                category_line_id = line_id
                                line_id += 1
                                for product in self.env['product.product'].browse(product_ids):

                                    column = []
                                    stop_current_execution = False

                                    owner = self.get_product_owner(product_id=product.id)

                                    if ownership in ['M', 'O']:
                                        if ownership == 'M' and 'O' == owner:
                                            continue
                                        elif ownership == 'O' and 'M' == owner:
                                            continue

                                    def insert_newline(string, index, addin):
                                        return string[:index] + addin + string[index:]

                                    product_name = product.name[:50] or product.name
                                    # quo = int(len(product.name) / 25) + 1
                                    # for x in range(quo):
                                    #     index = (x + 1) * 25 + x
                                    #     product_name = insert_newline(product_name, index, '<br/>')
                                    has_lots = False
                                    for line in sn_sp_all:
                                        if has_lots:
                                            break
                                        for key, val in line.items():
                                            if key == product.id and len(val[0]) > 1:
                                                has_lots = True
                                                break
                                    if not has_lots:
                                        for period in periods:
                                            period_date_from = period.get('date_from')
                                            period_date_to = period.get('date_to')

                                            product_sale_amount_list = self.get_sale_amount(period_date_from,
                                                                                            period_date_to,
                                                                                            product_id=product.id)
                                            product_sale_amount_list_pos = self.get_sale_amount_of_pos(period_date_from,
                                                                                                       period_date_to,
                                                                                                       product_id=product.id)
                                            product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                          product_sale_amount_list_pos[0]
                                            product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                          product_sale_amount_list_pos[1]
                                            product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                          product_sale_amount_list_pos[2]
                                            product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                          product_sale_amount_list_pos[3]

                                            product_cost_amount = product_sale_amount_list[0]
                                            product_invoice_amount = product_sale_amount_list[1]
                                            product_retail_sale = product_sale_amount_list[2]
                                            product_product_count = product_sale_amount_list[3]
                                            if not product_product_count:
                                                stop_current_execution = True
                                                break

                                            avg_count = product_sale_amount_list[4] + product_sale_amount_list_pos[4]

                                            # last year data
                                            ly_product_sale_amount_list = self.get_sale_amount(last_yr_date_from,
                                                                                               last_yr_date_to,
                                                                                               product_id=product.id)
                                            ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(
                                                last_yr_date_from,
                                                last_yr_date_to,
                                                product_id=product.id)
                                            ly_product_sale_amount_list[3] = ly_product_sale_amount_list[3] + \
                                                                             ly_product_sale_amount_list_pos[3]

                                            ly_product_product_count = ly_product_sale_amount_list[3]

                                            # last last year data
                                            lly_product_sale_amount_list = self.get_sale_amount(lly_date_from,
                                                                                                lly_date_to,
                                                                                                product_id=product.id)
                                            lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(
                                                lly_date_from,
                                                lly_date_to,
                                                product_id=product.id)
                                            lly_product_sale_amount_list[3] = lly_product_sale_amount_list[3] + \
                                                                              lly_product_sale_amount_list_pos[3]

                                            lly_product_product_count = lly_product_sale_amount_list[3]

                                            product_onhand_product_history = self.get_onhand_product_history(
                                                period_date_to,
                                                product_id=product.id)
                                            product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history

                                            if period_date_from == date_from:
                                                product_list = self.get_onhand_product(product=product)
                                                onhand_product_cost_amount = product_list[2] or 0
                                                sale_purchase_perc = 0
                                                if category_product_total and product_product_count:
                                                    sale_purchase_perc = product_product_count / (
                                                        category_product_total)
                                                sale_purchase_perc_sum += onhand_product_cost_amount
                                                sale_purchase_perc = str(
                                                    self.format_value(round(sale_purchase_perc * 100, 2))) + '%'

                                                product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                                product_sale_perc = str(
                                                    self.format_value(round(product_perc * 100, 2))) + '%'
                                                sale_perc_sum += product_perc
                                                column = [
                                                    {'name': product.default_code and product.default_code or ''},
                                                    {'name': '', 'class': 'text-left'},
                                                    {'name': owner},
                                                    {'name': ''},
                                                    {'name': product_sale_perc},
                                                    {'name': sale_purchase_perc},
                                                    {'name': int(product_product_count)},
                                                    {'name': self.dollar_format_value(
                                                        product.lst_price * int(product_product_count))},
                                                    # {'name': (self.format_value(product.lst_price)*product_product_count) },
                                                    # {'name': product_cost_amount },
                                                    # {'name': 0.0 },
                                                    # {'name': 0.0 ,'style':'border-right:1px solid black;'},
                                                    # {'name': self.format_value(product_old_onhand_qty)},
                                                    # {'name': self.format_value(product_old_onhand_cost),'style':'border-right:1px solid black;'},
                                                    # {'name': self.format_value(ly_product_product_count) },
                                                    # {'name': self.format_value(product.lst_price * ly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                    # {'name': self.format_value(lly_product_product_count) },
                                                    # {'name': self.format_value(product.lst_price * lly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                    # {'name': 0.0 },
                                                    # {'name': 0.0 },
                                                    # {'name': 0.0 },
                                                    # {'name': 0.0 },
                                                    # {'name':owner},
                                                    # {'name':product_name},
                                                    # {'name':self.get_vendor_reference(product)},
                                                    # {'name':self.format_value(product.lst_price)},
                                                    # {'name':product_product_count},
                                                    # {'name':product_sale_perc},
                                                    # {'name':sale_purchase_perc},
                                                    # {'name':'0.00'}
                                                ]
                                                retail_sum += (product.lst_price * int(product_product_count))

                                            invoice_sale_sum[period_date_from] += product_invoice_amount
                                            product_count_sum[period_date_from] += product_product_count
                                            retail_sale_sum[period_date_from] += product_retail_sale
                                            product_invoice_amount_formatted = self.dollar_format_value(
                                                product_invoice_amount)
                                            product_discount = product_retail_sale and (
                                                    product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                            # column += [
                                            # 	{'name':product_invoice_amount_formatted},
                                            # 	{'name':product_discount_perc}
                                            # 	]
                                            if period_date_from == date_from:
                                                average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                                gross_margin = product_invoice_amount - product_cost_amount
                                                gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                                product_cost_sum += product_cost_amount
                                                gross_margin_sum += gross_margin

                                                product_cost_amount_dol = product_cost_amount
                                                gross_margin_dol = gross_margin

                                                gross_margin_perc = str(
                                                    self.format_value(round(gross_margin_perc * 100, 2))) + '%'

                                                current_inventory = self.get_current_inventory(product=product)
                                                product_current_unit = current_inventory[0]
                                                product_current_cost = current_inventory[1]
                                                dts = self.get_dts_data(period_date_from, period_date_to,
                                                                        product=product)

                                                # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                                days_on_hand = self.get_day_on_hand(product=product)
                                                shown = self.get_crm_shown(period_date_from, period_date_to,
                                                                           product=product)
                                                avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                                gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                                turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                                column += [
                                                    {'name': product_invoice_amount_formatted},
                                                    {'name': self.dollar_format_value(product_cost_amount)},
                                                    {'name': self.dollar_format_value(gross_margin)},
                                                    {'name': gross_margin_perc},
                                                    {'name': int(
                                                        dts / product_product_count if product_product_count else 0)},
                                                    {'name': self.format_value(
                                                        gmroi / product_product_count if product_product_count else 0)},
                                                    {'name': self.format_value(
                                                        turn / product_product_count if product_product_count else 0)},
                                                    {'name': int(shown)},
                                                    {'name': int(ly_product_product_count),
                                                     'class': 'border-left  number'},
                                                    {'name': self.dollar_format_value(
                                                        product.lst_price * ly_product_product_count)},
                                                    {'name': int(lly_product_product_count),
                                                     'class': 'border-left  number'},
                                                    {'name': self.dollar_format_value(
                                                        product.lst_price * lly_product_product_count)},
                                                    {'name': int(product_current_unit), 'class': 'border-left  number'},
                                                    {'name': self.dollar_format_value(product_current_cost)},
                                                    # {'name': self.format_value(aged_inventory) + '%'},
                                                    {'name': int(
                                                        days_on_hand / product_product_count if product_product_count else 0)},
                                                ]
                                                for line in sn_sp_all:
                                                    for key, val in line.items():
                                                        if key == product.id and len(val[0]) == 1 and len(val[1]) == 1:
                                                            column[1].update({'name': val[0][0]})
                                                            column[3].update({'name': val[1][0]})
                                                        if key == product.id and len(val[1]) == 1:
                                                            column[3].update({'name': val[1][0]})
                                                        if key == product.id and len(val[1]) > 1 and not val[0]:
                                                            column[3].update({'name': ",".join(val[1])})
                                                        if key == product.id and len(val[1]) > 1 and val[0]:
                                                            column[3].update({'name': ",".join(val[1])})
                                                # for line in sn_sp_all[0]:
                                                # 	for key, val in line.items():
                                                # 		if key == product.id and len(val)==1:
                                                # 			column[1].update({'name': val[0]})
                                                # for line in sn_sp_all[1]:
                                                # 	for key, val in line.items():
                                                # 		if key == product.id and len(val)==1:
                                                # 			column[3].update({'name': val[0]})

                                                product_list = self.get_onhand_product(product=product)
                                                product_available_qty = product_list[0]
                                                product_available_product_price = product_list[1]
                                                product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                                product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                                product_available_qty_sum += product_available_qty
                                                product_available_qty_perc_sum += product_available_qty_perc
                                                product_available_product_price_sum += product_available_product_price
                                                product_avg_on_hand_price_sum += product_avg_on_hand_price

                                                total_gmroi += gmroi
                                                total_turn += turn
                                                total_shown += shown
                                                total_dts += dts
                                                total_period_oh += product_old_onhand_qty
                                                total_period_cogs += product_old_onhand_cost
                                                total_ly_units += ly_product_product_count
                                                total_ly_amnt += (product.lst_price * ly_product_product_count)

                                                total_lly_units += lly_product_product_count
                                                total_lly_amnt += (product.lst_price * lly_product_product_count)

                                                invt_unit += product_current_unit
                                                invt_cost += product_current_cost
                                                # invt_aged += aged_inventory
                                                invt_doh += days_on_hand
                                                total_categ_dict.update({category.id:
                                                                             {'categ_product_count':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_count'] + product_product_count,
                                                                              'categ_product_retail':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_retail'] + (
                                                                                          product.lst_price * product_product_count),
                                                                              'categ_product_sale_ly':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_sale_ly'] + (
                                                                                          ly_product_product_count * product.lst_price),
                                                                              'categ_product_sale_lly':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_sale_lly'] + (
                                                                                          product.lst_price * lly_product_product_count),
                                                                              'categ_product_invoice_amount':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_invoice_amount'] + product_invoice_amount,
                                                                              'categ_product_cost_amount':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_cost_amount'] + product_cost_amount,
                                                                              'categ_gross_margin':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_gross_margin'] + gross_margin,
                                                                              'categ_dts':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_dts'] + dts,
                                                                              'categ_gmroi':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_gmroi'] + gmroi,
                                                                              'categ_turn':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_turn'] + turn,
                                                                              'categ_shown':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_shown'] + shown,
                                                                              'categ_product_old_onhand_qty':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                              'categ_product_old_onhand_cost':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                              'categ_ly_product_product_count':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_ly_product_product_count'] + ly_product_product_count,
                                                                              'categ_lly_product_product_count':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_lly_product_product_count'] + lly_product_product_count,
                                                                              'categ_product_current_unit':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_current_unit'] + product_current_unit,
                                                                              'categ_product_current_cost':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_product_current_cost'] + product_current_cost,
                                                                              'categ_days_on_hand':
                                                                                  total_categ_dict[category.id][
                                                                                      'categ_days_on_hand'] + days_on_hand}})
                                                total_categ_dict.update({sub_category.id:
                                                                             {'categ_product_count':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_count'] + product_product_count,
                                                                              'categ_product_retail':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_retail'] + (
                                                                                          product.lst_price * product_product_count),
                                                                              'categ_product_sale_ly':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_sale_ly'] + (
                                                                                          ly_product_product_count * product.lst_price),
                                                                              'categ_product_sale_lly':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_sale_lly'] + (
                                                                                          product.lst_price * lly_product_product_count),
                                                                              'categ_product_invoice_amount':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_invoice_amount'] + product_invoice_amount,
                                                                              'categ_product_cost_amount':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_cost_amount'] + product_cost_amount,
                                                                              'categ_gross_margin':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_gross_margin'] + gross_margin,
                                                                              'categ_dts':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_dts'] + dts,
                                                                              'categ_gmroi':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_gmroi'] + gmroi,
                                                                              'categ_turn':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_turn'] + turn,
                                                                              'categ_shown':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_shown'] + shown,
                                                                              'categ_product_old_onhand_qty':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                              'categ_product_old_onhand_cost':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                              'categ_ly_product_product_count':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_ly_product_product_count'] + ly_product_product_count,
                                                                              'categ_lly_product_product_count':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_lly_product_product_count'] + lly_product_product_count,
                                                                              'categ_product_current_unit':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_current_unit'] + product_current_unit,
                                                                              'categ_product_current_cost':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_product_current_cost'] + product_current_cost,
                                                                              'categ_days_on_hand':
                                                                                  total_categ_dict[sub_category.id][
                                                                                      'categ_days_on_hand'] + days_on_hand}})
                                                total_categ_dict.update({parent_categ.id:
                                                    {
                                                        # 'categ_product_count':
                                                        #  total_categ_dict[parent_categ.id][
                                                        #      'categ_product_count'] + product_product_count,
                                                        # 'categ_product_retail':
                                                        #     total_categ_dict[parent_categ.id][
                                                        #         'categ_product_retail'] + (
                                                        #             product.lst_price * int(
                                                        #         product_product_count)),
                                                        'categ_product_sale_ly':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_sale_ly'] + (
                                                                    ly_product_product_count * product.lst_price),
                                                        'categ_product_sale_lly':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_sale_lly'] + (
                                                                    product.lst_price * lly_product_product_count),
                                                        'categ_product_invoice_amount':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_invoice_amount'] + product_invoice_amount,
                                                        # 'categ_product_cost_amount':
                                                        #     total_categ_dict[parent_categ.id][
                                                        #         'categ_product_cost_amount'] + product_cost_amount,
                                                        'categ_gross_margin':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_gross_margin'] + gross_margin,
                                                        'categ_dts':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_dts'] + dts,
                                                        'categ_gmroi':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_gmroi'] + gmroi,
                                                        'categ_turn':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_turn'] + turn,
                                                        'categ_shown':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_shown'] + shown,
                                                        'categ_product_old_onhand_qty':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                        'categ_product_old_onhand_cost':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                        'categ_ly_product_product_count':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_ly_product_product_count'] + ly_product_product_count,
                                                        'categ_lly_product_product_count':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_lly_product_product_count'] + lly_product_product_count,
                                                        'categ_product_current_unit':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_current_unit'] + product_current_unit,
                                                        'categ_product_current_cost':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_product_current_cost'] + product_current_cost,
                                                        'categ_days_on_hand':
                                                            total_categ_dict[parent_categ.id][
                                                                'categ_days_on_hand'] + days_on_hand}})

                                        if stop_current_execution:
                                            continue

                                        lines.append({
                                            'id': line_id,
                                            'name': product_name,
                                            'unfoldable': False,
                                            'class': 'vendor_int',
                                            'columns': column,
                                            'level': product_line_level,

                                        })

                                        line_id += 1
                                    else:
                                        for line in sn_sp_all:
                                            for key, val in line.items():
                                                if key == product.id and len(val[0]) > 1:
                                                    for data in val[0]:
                                                        for period in periods:
                                                            period_date_from = period.get('date_from')
                                                            period_date_to = period.get('date_to')

                                                            product_sale_amount_list = self.get_sale_amount_for_lot(
                                                                period_date_from,
                                                                period_date_to,
                                                                product_id=product.id, lot=data)
                                                            product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                                period_date_from,
                                                                period_date_to,
                                                                product_id=product.id, lot=data)
                                                            product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                                          product_sale_amount_list_pos[
                                                                                              0]
                                                            product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                                          product_sale_amount_list_pos[
                                                                                              1]
                                                            product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                                          product_sale_amount_list_pos[
                                                                                              2]
                                                            product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                                          product_sale_amount_list_pos[
                                                                                              3]

                                                            product_cost_amount = product_sale_amount_list[0]
                                                            product_invoice_amount = product_sale_amount_list[1]
                                                            product_retail_sale = product_sale_amount_list[2]
                                                            product_product_count = product_sale_amount_list[3]
                                                            if not product_product_count:
                                                                stop_current_execution = True
                                                                break

                                                            avg_count = product_sale_amount_list[4] + \
                                                                        product_sale_amount_list_pos[4]

                                                            # last year data
                                                            ly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                                last_yr_date_from,
                                                                last_yr_date_to,
                                                                product_id=product.id, lot=data)
                                                            ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                                last_yr_date_from,
                                                                last_yr_date_to,
                                                                product_id=product.id, lot=data)
                                                            ly_product_sale_amount_list[3] = \
                                                                ly_product_sale_amount_list[
                                                                    3] + \
                                                                ly_product_sale_amount_list_pos[
                                                                    3]

                                                            ly_product_product_count = ly_product_sale_amount_list[3]

                                                            # last last year data
                                                            lly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                                lly_date_from, lly_date_to,
                                                                product_id=product.id, lot=data)
                                                            lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                                lly_date_from,
                                                                lly_date_to,
                                                                product_id=product.id, lot=data)
                                                            lly_product_sale_amount_list[3] = \
                                                                lly_product_sale_amount_list[
                                                                    3] + \
                                                                lly_product_sale_amount_list_pos[
                                                                    3]

                                                            lly_product_product_count = lly_product_sale_amount_list[3]

                                                            product_onhand_product_history = self.get_onhand_product_history_for_lot(
                                                                period_date_to,
                                                                product_id=product.id, lot=data)
                                                            product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history

                                                            if period_date_from == date_from:
                                                                product_list = self.get_onhand_product_for_lot(
                                                                    product=product, lot=data)
                                                                onhand_product_cost_amount = product_list[2] or 0
                                                                sale_purchase_perc = 0
                                                                if category_product_total and product_product_count:
                                                                    sale_purchase_perc = product_product_count / (
                                                                        category_product_total)
                                                                sale_purchase_perc_sum += onhand_product_cost_amount
                                                                sale_purchase_perc = str(
                                                                    self.format_value(
                                                                        round(sale_purchase_perc * 100, 2))) + '%'

                                                                product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                                                product_sale_perc = str(
                                                                    self.format_value(
                                                                        round(product_perc * 100, 2))) + '%'
                                                                sale_perc_sum += product_perc
                                                                column = [
                                                                    {
                                                                        'name': product.default_code and product.default_code or ''},
                                                                    {'name': '', 'class': 'text-left'},
                                                                    {'name': owner},
                                                                    {'name': ''},
                                                                    {'name': product_sale_perc},
                                                                    {'name': sale_purchase_perc},
                                                                    {'name': int(product_product_count)},
                                                                    {'name': self.dollar_format_value(
                                                                        product.lst_price * int(
                                                                            product_product_count))},
                                                                    # {'name': (self.format_value(product.lst_price)*product_product_count) },
                                                                    # {'name': product_cost_amount },
                                                                    # {'name': 0.0 },
                                                                    # {'name': 0.0 ,'style':'border-right:1px solid black;'},
                                                                    # {'name': self.format_value(product_old_onhand_qty)},
                                                                    # {'name': self.format_value(product_old_onhand_cost),'style':'border-right:1px solid black;'},
                                                                    # {'name': self.format_value(ly_product_product_count) },
                                                                    # {'name': self.format_value(product.lst_price * ly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                                    # {'name': self.format_value(lly_product_product_count) },
                                                                    # {'name': self.format_value(product.lst_price * lly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                                    # {'name': 0.0 },
                                                                    # {'name': 0.0 },
                                                                    # {'name': 0.0 },
                                                                    # {'name': 0.0 },
                                                                    # {'name':owner},
                                                                    # {'name':product_name},
                                                                    # {'name':self.get_vendor_reference(product)},
                                                                    # {'name':self.format_value(product.lst_price)},
                                                                    # {'name':product_product_count},
                                                                    # {'name':product_sale_perc},
                                                                    # {'name':sale_purchase_perc},
                                                                    # {'name':'0.00'}
                                                                ]
                                                                retail_sum += (product.lst_price * int(
                                                                    product_product_count))

                                                            invoice_sale_sum[period_date_from] += product_invoice_amount
                                                            product_count_sum[period_date_from] += product_product_count
                                                            retail_sale_sum[period_date_from] += product_retail_sale
                                                            product_invoice_amount_formatted = self.dollar_format_value(
                                                                product_invoice_amount)
                                                            product_discount = product_retail_sale and (
                                                                    product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                                            # column += [
                                                            # 	{'name':product_invoice_amount_formatted},
                                                            # 	{'name':product_discount_perc}
                                                            # 	]
                                                            if period_date_from == date_from:
                                                                average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                                                gross_margin = product_invoice_amount - product_cost_amount
                                                                gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                                                product_cost_sum += product_cost_amount
                                                                gross_margin_sum += gross_margin

                                                                product_cost_amount_dol = product_cost_amount
                                                                gross_margin_dol = gross_margin

                                                                gross_margin_perc = str(
                                                                    self.format_value(
                                                                        round(gross_margin_perc * 100, 2))) + '%'

                                                                current_inventory = self.get_current_inventory_for_lot(
                                                                    product=product, lot=data)
                                                                product_current_unit = current_inventory[0]
                                                                product_current_cost = current_inventory[1]
                                                                dts = self.get_dts_data_for_lot(period_date_from,
                                                                                                period_date_to,
                                                                                                product=product,
                                                                                                lot=data)

                                                                # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                                                days_on_hand = self.get_day_on_hand_for_lot(
                                                                    product=product,
                                                                    lot=data)
                                                                shown = self.get_crm_shown(period_date_from,
                                                                                           period_date_to,
                                                                                           product=product)
                                                                avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                                                gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                                                turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                                                column += [
                                                                    {'name': product_invoice_amount_formatted},
                                                                    {'name': self.dollar_format_value(
                                                                        product_cost_amount)},
                                                                    {'name': self.dollar_format_value(gross_margin)},
                                                                    {'name': gross_margin_perc},
                                                                    {'name': int(
                                                                        dts / product_product_count if product_product_count else 0)},
                                                                    {'name': self.format_value(
                                                                        gmroi / product_product_count if product_product_count else 0)},
                                                                    {'name': self.format_value(
                                                                        turn / product_product_count if product_product_count else 0)},
                                                                    {'name': int(shown)},
                                                                    {'name': int(ly_product_product_count),
                                                                     'class': 'border-left  number'},
                                                                    {'name': self.dollar_format_value(
                                                                        product.lst_price * ly_product_product_count)},
                                                                    {'name': int(lly_product_product_count),
                                                                     'class': 'border-left  number'},
                                                                    {'name': self.dollar_format_value(
                                                                        product.lst_price * lly_product_product_count)},
                                                                    {'name': int(product_current_unit),
                                                                     'class': 'border-left  number'},
                                                                    {'name': self.dollar_format_value(
                                                                        product_current_cost)},
                                                                    # {'name': self.format_value(aged_inventory) + '%'},
                                                                    {'name': int(
                                                                        days_on_hand / product_product_count if product_product_count else 0)},
                                                                ]

                                                                if len(val[1]) == 1:
                                                                    column[3].update({'name': val[1][0]})
                                                                if len(val[1]) > 1:
                                                                    column[3].update({'name': ",".join(val[1])})
                                                                column[1].update({'name': data})
                                                                # for line in sn_sp_all[0]:
                                                                # 	for key, val in line.items():
                                                                # 		if key == product.id and len(val)==1:
                                                                # 			column[1].update({'name': val[0]})
                                                                # for line in sn_sp_all[1]:
                                                                # 	for key, val in line.items():
                                                                # 		if key == product.id and len(val)==1:
                                                                # 			column[3].update({'name': val[0]})

                                                                product_list = self.get_onhand_product_for_lot(
                                                                    product=product, lot=data)
                                                                product_available_qty = product_list[0]
                                                                product_available_product_price = product_list[1]
                                                                product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                                                product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                                                product_available_qty_sum += product_available_qty
                                                                product_available_qty_perc_sum += product_available_qty_perc
                                                                product_available_product_price_sum += product_available_product_price
                                                                product_avg_on_hand_price_sum += product_avg_on_hand_price

                                                                total_gmroi += gmroi
                                                                total_turn += turn
                                                                total_shown += shown
                                                                total_dts += dts
                                                                total_period_oh += product_old_onhand_qty
                                                                total_period_cogs += product_old_onhand_cost
                                                                total_ly_units += ly_product_product_count
                                                                total_ly_amnt += (
                                                                        product.lst_price * ly_product_product_count)

                                                                total_lly_units += lly_product_product_count
                                                                total_lly_amnt += (
                                                                        product.lst_price * lly_product_product_count)

                                                                invt_unit += product_current_unit
                                                                invt_cost += product_current_cost
                                                                # invt_aged += aged_inventory
                                                                invt_doh += days_on_hand
                                                                total_categ_dict.update({category.id:
                                                                                             {'categ_product_count':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_count'] + product_product_count,
                                                                                              'categ_product_retail':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_retail'] + (
                                                                                                          product.lst_price * int(
                                                                                                      product_product_count)),
                                                                                              'categ_product_sale_ly':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_sale_ly'] + (
                                                                                                          ly_product_product_count * product.lst_price),
                                                                                              'categ_product_sale_lly':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_sale_lly'] + (
                                                                                                          product.lst_price * lly_product_product_count),
                                                                                              'categ_product_invoice_amount':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                              'categ_product_cost_amount':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_cost_amount'] + product_cost_amount,
                                                                                              'categ_gross_margin':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_gross_margin'] + gross_margin,
                                                                                              'categ_dts':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_dts'] + dts,
                                                                                              'categ_gmroi':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_gmroi'] + gmroi,
                                                                                              'categ_turn':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_turn'] + turn,
                                                                                              'categ_shown':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_shown'] + shown,
                                                                                              'categ_product_old_onhand_qty':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                              'categ_product_old_onhand_cost':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                              'categ_ly_product_product_count':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                              'categ_lly_product_product_count':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                              'categ_product_current_unit':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_current_unit'] + product_current_unit,
                                                                                              'categ_product_current_cost':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_product_current_cost'] + product_current_cost,
                                                                                              'categ_days_on_hand':
                                                                                                  total_categ_dict[
                                                                                                      category.id][
                                                                                                      'categ_days_on_hand'] + days_on_hand}})
                                                                total_categ_dict.update({sub_category.id:
                                                                                             {'categ_product_count':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_count'] + product_product_count,
                                                                                              'categ_product_retail':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_retail'] + (
                                                                                                          product.lst_price * int(
                                                                                                      product_product_count)),
                                                                                              'categ_product_sale_ly':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_sale_ly'] + (
                                                                                                          ly_product_product_count * product.lst_price),
                                                                                              'categ_product_sale_lly':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_sale_lly'] + (
                                                                                                          product.lst_price * lly_product_product_count),
                                                                                              'categ_product_invoice_amount':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                              'categ_product_cost_amount':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_cost_amount'] + product_cost_amount,
                                                                                              'categ_gross_margin':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_gross_margin'] + gross_margin,
                                                                                              'categ_dts':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_dts'] + dts,
                                                                                              'categ_gmroi':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_gmroi'] + gmroi,
                                                                                              'categ_turn':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_turn'] + turn,
                                                                                              'categ_shown':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_shown'] + shown,
                                                                                              'categ_product_old_onhand_qty':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                              'categ_product_old_onhand_cost':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                              'categ_ly_product_product_count':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                              'categ_lly_product_product_count':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                              'categ_product_current_unit':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_current_unit'] + product_current_unit,
                                                                                              'categ_product_current_cost':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_product_current_cost'] + product_current_cost,
                                                                                              'categ_days_on_hand':
                                                                                                  total_categ_dict[
                                                                                                      sub_category.id][
                                                                                                      'categ_days_on_hand'] + days_on_hand}})
                                                                total_categ_dict.update({
                                                                    # parent_categ.id:
                                                                    #  {'categ_product_count':
                                                                    #       total_categ_dict[
                                                                    #           parent_categ.id][
                                                                    #           'categ_product_count'] + product_product_count,
                                                                    #   'categ_product_retail':
                                                                    #       total_categ_dict[
                                                                    #           parent_categ.id][
                                                                    #           'categ_product_retail'] + (
                                                                    #               product.lst_price * int(
                                                                    #           product_product_count)),
                                                                    'categ_product_sale_ly':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_sale_ly'] + (
                                                                                ly_product_product_count * product.lst_price),
                                                                    'categ_product_sale_lly':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_sale_lly'] + (
                                                                                product.lst_price * lly_product_product_count),
                                                                    'categ_product_invoice_amount':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_invoice_amount'] + product_invoice_amount,
                                                                    # 'categ_product_cost_amount':
                                                                    #     total_categ_dict[
                                                                    #         parent_categ.id][
                                                                    #         'categ_product_cost_amount'] + product_cost_amount,
                                                                    'categ_gross_margin':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_gross_margin'] + gross_margin,
                                                                    'categ_dts':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_dts'] + dts,
                                                                    'categ_gmroi':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_gmroi'] + gmroi,
                                                                    'categ_turn':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_turn'] + turn,
                                                                    'categ_shown':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_shown'] + shown,
                                                                    'categ_product_old_onhand_qty':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                    'categ_product_old_onhand_cost':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                    'categ_ly_product_product_count':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_ly_product_product_count'] + ly_product_product_count,
                                                                    'categ_lly_product_product_count':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_lly_product_product_count'] + lly_product_product_count,
                                                                    'categ_product_current_unit':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_current_unit'] + product_current_unit,
                                                                    'categ_product_current_cost':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_product_current_cost'] + product_current_cost,
                                                                    'categ_days_on_hand':
                                                                        total_categ_dict[
                                                                            parent_categ.id][
                                                                            'categ_days_on_hand'] + days_on_hand})

                                                        if stop_current_execution:
                                                            continue

                                                        lines.append({
                                                            'id': line_id,
                                                            'name': product_name,
                                                            'unfoldable': False,
                                                            'class': 'vendor_int',
                                                            'columns': column,
                                                            'level': product_line_level,

                                                        })

                                                        line_id += 1
                                categ_gross_margin_perc = total_categ_dict[category.id][
                                                              'categ_product_invoice_amount'] and \
                                                          total_categ_dict[category.id]['categ_gross_margin'] / \
                                                          total_categ_dict[category.id][
                                                              'categ_product_invoice_amount'] or 0
                                categ_column = [
                                    {'name': ''},
                                    {'name': ''},
                                    {'name': ''},
                                    {'name': ''},
                                    {'name': ''},
                                    {'name': ''},
                                    {'name': int(total_categ_dict[category.id]['categ_product_count'])},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_product_retail'])},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_product_invoice_amount'])},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_product_cost_amount'])},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_gross_margin'])},
                                    {'name': str(self.format_value(round(categ_gross_margin_perc * 100, 2))) + '%'},
                                    {'name': int(total_categ_dict[category.id]['categ_dts'] /
                                                 total_categ_dict[category.id][
                                                     'categ_product_count'] if total_categ_dict[category.id][
                                        'categ_product_count'] else 0)},
                                    {'name': self.format_value(
                                        total_categ_dict[category.id]['categ_gmroi'] /
                                        total_categ_dict[category.id][
                                            'categ_product_count'] if total_categ_dict[category.id][
                                            'categ_product_count'] else 0)},
                                    {'name': self.format_value(
                                        total_categ_dict[category.id]['categ_turn'] /
                                        total_categ_dict[category.id][
                                            'categ_product_count'] if total_categ_dict[category.id][
                                            'categ_product_count'] else 0)},
                                    {'name': int(total_categ_dict[category.id]['categ_shown'])},
                                    {'name': int(total_categ_dict[category.id]['categ_ly_product_product_count']),
                                     'class': 'border-left  number'},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_product_sale_ly'])},
                                    {'name': int(total_categ_dict[category.id]['categ_lly_product_product_count']),
                                     'class': 'border-left  number'},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_product_sale_lly'])},
                                    {'name': int(total_categ_dict[category.id]['categ_product_current_unit']),
                                     'class': 'border-left  number'},
                                    {'name': self.dollar_format_value(
                                        total_categ_dict[category.id]['categ_product_current_cost'])},
                                    {'name': int(
                                        total_categ_dict[category.id]['categ_days_on_hand'] /
                                        total_categ_dict[category.id][
                                            'categ_product_count'] if total_categ_dict[category.id][
                                            'categ_product_count'] else 0)}, ]
                                lines.append({
                                    'id': category_line_id,
                                    'name': category.complete_name,
                                    'unfoldable': False,
                                    'class': 'o_account_reports_level1',
                                    'title_hover': _('category'),
                                    'level': category_level,
                                    'columns': categ_column,
                                })
                            for child_category in category.child_id:
                                if str(child_category.id) in all_categ:
                                    child_category_level = 4
                                    product_line_level = 5
                                    category_total_level = 4
                                    total_categ_dict.update({child_category.id: {'categ_product_count': 0,
                                                                                 'categ_product_retail': 0,
                                                                                 'categ_product_sale_ly': 0,
                                                                                 'categ_product_sale_lly': 0,
                                                                                 'categ_product_invoice_amount': 0,
                                                                                 'categ_product_cost_amount': 0,
                                                                                 'categ_gross_margin': 0,
                                                                                 'categ_dts': 0,
                                                                                 'categ_gmroi': 0,
                                                                                 'categ_turn': 0,
                                                                                 'categ_shown': 0,
                                                                                 'categ_product_old_onhand_qty': 0,
                                                                                 'categ_product_old_onhand_cost': 0,
                                                                                 'categ_ly_product_product_count': 0,
                                                                                 'categ_lly_product_product_count': 0,
                                                                                 'categ_product_current_unit': 0,
                                                                                 'categ_product_current_cost': 0,
                                                                                 'categ_days_on_hand': 0
                                                                                 }})
                                    product_ids = self.get_product_ids(date_from, date_to, vendor_ids,
                                                                       child_category.id)
                                    if product_ids:
                                        category_product_total = self.get_category_count_of_products(date_from, date_to,
                                                                                                     product_ids=product_ids)
                                        child_category_line_id = line_id
                                        line_id += 1
                                        for product in self.env['product.product'].browse(product_ids):
                                            column = []
                                            stop_current_execution = False

                                            owner = self.get_product_owner(product_id=product.id)

                                            if ownership in ['M', 'O']:
                                                if ownership == 'M' and 'O' == owner:
                                                    continue
                                                elif ownership == 'O' and 'M' == owner:
                                                    continue

                                            def insert_newline(string, index, addin):
                                                return string[:index] + addin + string[index:]

                                            product_name = product.name[:50] or product.name
                                            # quo = int(len(product.name) / 25) + 1
                                            # for x in range(quo):
                                            #     index = (x + 1) * 25 + x
                                            #     product_name = insert_newline(product_name, index, '<br/>')
                                            has_lots = False
                                            for line in sn_sp_all:
                                                if has_lots:
                                                    break
                                                for key, val in line.items():
                                                    if key == product.id and len(val[0]) > 1:
                                                        has_lots = True
                                                        break
                                            if not has_lots:
                                                for period in periods:
                                                    period_date_from = period.get('date_from')
                                                    period_date_to = period.get('date_to')

                                                    product_sale_amount_list = self.get_sale_amount(period_date_from,
                                                                                                    period_date_to,
                                                                                                    product_id=product.id)
                                                    product_sale_amount_list_pos = self.get_sale_amount_of_pos(
                                                        period_date_from,
                                                        period_date_to,
                                                        product_id=product.id)
                                                    product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                                  product_sale_amount_list_pos[0]
                                                    product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                                  product_sale_amount_list_pos[1]
                                                    product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                                  product_sale_amount_list_pos[2]
                                                    product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                                  product_sale_amount_list_pos[3]

                                                    product_cost_amount = product_sale_amount_list[0]
                                                    product_invoice_amount = product_sale_amount_list[1]
                                                    product_retail_sale = product_sale_amount_list[2]
                                                    product_product_count = product_sale_amount_list[3]
                                                    if not product_product_count:
                                                        stop_current_execution = True
                                                        break

                                                    avg_count = product_sale_amount_list[4] + \
                                                                product_sale_amount_list_pos[4]

                                                    # last year data
                                                    ly_product_sale_amount_list = self.get_sale_amount(
                                                        last_yr_date_from,
                                                        last_yr_date_to,
                                                        product_id=product.id)
                                                    ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(
                                                        last_yr_date_from,
                                                        last_yr_date_to,
                                                        product_id=product.id)
                                                    ly_product_sale_amount_list[3] = ly_product_sale_amount_list[3] + \
                                                                                     ly_product_sale_amount_list_pos[3]

                                                    ly_product_product_count = ly_product_sale_amount_list[3]

                                                    # last last year data
                                                    lly_product_sale_amount_list = self.get_sale_amount(lly_date_from,
                                                                                                        lly_date_to,
                                                                                                        product_id=product.id)
                                                    lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos(
                                                        lly_date_from,
                                                        lly_date_to,
                                                        product_id=product.id)
                                                    lly_product_sale_amount_list[3] = lly_product_sale_amount_list[3] + \
                                                                                      lly_product_sale_amount_list_pos[
                                                                                          3]

                                                    lly_product_product_count = lly_product_sale_amount_list[3]

                                                    product_onhand_product_history = self.get_onhand_product_history(
                                                        period_date_to,
                                                        product_id=product.id)
                                                    product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history

                                                    if period_date_from == date_from:
                                                        product_list = self.get_onhand_product(product=product)
                                                        onhand_product_cost_amount = product_list[2] or 0
                                                        sale_purchase_perc = 0
                                                        if category_product_total and product_product_count:
                                                            sale_purchase_perc = product_product_count / (
                                                                category_product_total)
                                                        sale_purchase_perc_sum += onhand_product_cost_amount
                                                        sale_purchase_perc = str(
                                                            self.format_value(round(sale_purchase_perc * 100, 2))) + '%'

                                                        product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                                        product_sale_perc = str(
                                                            self.format_value(round(product_perc * 100, 2))) + '%'
                                                        sale_perc_sum += product_perc
                                                        column = [
                                                            {
                                                                'name': product.default_code and product.default_code or ''},
                                                            {'name': '', 'class': 'text-left'},
                                                            {'name': owner},
                                                            {'name': ''},
                                                            {'name': product_sale_perc},
                                                            {'name': sale_purchase_perc},
                                                            {'name': int(product_product_count)},
                                                            {'name': self.dollar_format_value(product.lst_price)},
                                                            # {'name': (self.format_value(product.lst_price)*product_product_count) },
                                                            # {'name': product_cost_amount },
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 ,'style':'border-right:1px solid black;'},
                                                            # {'name': self.format_value(product_old_onhand_qty)},
                                                            # {'name': self.format_value(product_old_onhand_cost),'style':'border-right:1px solid black;'},
                                                            # {'name': self.format_value(ly_product_product_count) },
                                                            # {'name': self.format_value(product.lst_price * ly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                            # {'name': self.format_value(lly_product_product_count) },
                                                            # {'name': self.format_value(product.lst_price * lly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 },
                                                            # {'name': 0.0 },
                                                            # {'name':owner},
                                                            # {'name':product_name},
                                                            # {'name':self.get_vendor_reference(product)},
                                                            # {'name':self.format_value(product.lst_price)},
                                                            # {'name':product_product_count},
                                                            # {'name':product_sale_perc},
                                                            # {'name':sale_purchase_perc},
                                                            # {'name':'0.00'}
                                                        ]
                                                        retail_sum += (product.lst_price * int(product_product_count))

                                                    invoice_sale_sum[period_date_from] += product_invoice_amount
                                                    product_count_sum[period_date_from] += product_product_count
                                                    retail_sale_sum[period_date_from] += product_retail_sale
                                                    product_invoice_amount_formatted = self.dollar_format_value(
                                                        product_invoice_amount)
                                                    product_discount = product_retail_sale and (
                                                            product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                                    # column += [
                                                    # 	{'name':product_invoice_amount_formatted},
                                                    # 	{'name':product_discount_perc}
                                                    # 	]
                                                    if period_date_from == date_from:
                                                        average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                                        gross_margin = product_invoice_amount - product_cost_amount
                                                        gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                                        product_cost_sum += product_cost_amount
                                                        gross_margin_sum += gross_margin

                                                        product_cost_amount_dol = product_cost_amount
                                                        gross_margin_dol = gross_margin

                                                        gross_margin_perc = str(
                                                            self.format_value(round(gross_margin_perc * 100, 2))) + '%'

                                                        current_inventory = self.get_current_inventory(product=product)
                                                        product_current_unit = current_inventory[0]
                                                        product_current_cost = current_inventory[1]
                                                        dts = self.get_dts_data(period_date_from, period_date_to,
                                                                                product=product)

                                                        # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                                        days_on_hand = self.get_day_on_hand(product=product)
                                                        shown = self.get_crm_shown(period_date_from, period_date_to,
                                                                                   product=product)
                                                        avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                                        gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                                        turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                                        column += [
                                                            {'name': product_invoice_amount_formatted},
                                                            {'name': self.dollar_format_value(product_cost_amount)},
                                                            {'name': self.dollar_format_value(gross_margin)},
                                                            {'name': gross_margin_perc},
                                                            {'name': int(
                                                                dts / product_product_count if product_product_count else 0)},
                                                            {'name': self.format_value(
                                                                gmroi / product_product_count if product_product_count else 0)},
                                                            {'name': self.format_value(
                                                                turn / product_product_count if product_product_count else 0)},
                                                            {'name': int(shown)},
                                                            {'name': int(ly_product_product_count),
                                                             'class': 'border-left  number'},
                                                            {'name': self.dollar_format_value(
                                                                product.lst_price * ly_product_product_count)},
                                                            {'name': int(lly_product_product_count),
                                                             'class': 'border-left  number'},
                                                            {'name': self.dollar_format_value(
                                                                product.lst_price * lly_product_product_count)},
                                                            {'name': int(product_current_unit),
                                                             'class': 'border-left  number'},
                                                            {'name': self.dollar_format_value(product_current_cost)},
                                                            # {'name': self.format_value(aged_inventory) + '%'},
                                                            {'name': int(
                                                                days_on_hand / product_product_count if product_product_count else 0)},
                                                        ]
                                                        for line in sn_sp_all:
                                                            for key, val in line.items():
                                                                if key == product.id and len(val[0]) == 1 and len(
                                                                        val[1]) == 1:
                                                                    column[1].update({'name': val[0][0]})
                                                                    column[3].update({'name': val[1][0]})
                                                                if key == product.id and len(val[1]) == 1:
                                                                    column[3].update({'name': val[1][0]})
                                                                if key == product.id and len(val[1]) > 1 and not val[0]:
                                                                    column[3].update({'name': ",".join(val[1])})
                                                                if key == product.id and len(val[1]) > 1 and val[0]:
                                                                    column[3].update({'name': ",".join(val[1])})
                                                        # for line in sn_sp_all[0]:
                                                        # 	for key, val in line.items():
                                                        # 		if key == product.id and len(val)==1:
                                                        # 			column[1].update({'name': val[0]})
                                                        # for line in sn_sp_all[1]:
                                                        # 	for key, val in line.items():
                                                        # 		if key == product.id and len(val)==1:
                                                        # 			column[3].update({'name': val[0]})

                                                        product_list = self.get_onhand_product(product=product)
                                                        product_available_qty = product_list[0]
                                                        product_available_product_price = product_list[1]
                                                        product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                                        product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                                        product_available_qty_sum += product_available_qty
                                                        product_available_qty_perc_sum += product_available_qty_perc
                                                        product_available_product_price_sum += product_available_product_price
                                                        product_avg_on_hand_price_sum += product_avg_on_hand_price

                                                        total_gmroi += gmroi
                                                        total_turn += turn
                                                        total_shown += shown
                                                        total_dts += dts
                                                        total_period_oh += product_old_onhand_qty
                                                        total_period_cogs += product_old_onhand_cost
                                                        total_ly_units += ly_product_product_count
                                                        total_ly_amnt += (product.lst_price * ly_product_product_count)

                                                        total_lly_units += lly_product_product_count
                                                        total_lly_amnt += (
                                                                product.lst_price * lly_product_product_count)

                                                        invt_unit += product_current_unit
                                                        invt_cost += product_current_cost
                                                        # invt_aged += aged_inventory
                                                        invt_doh += days_on_hand
                                                        total_categ_dict.update({child_category.id:
                                                                                     {'categ_product_count':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_count'] + product_product_count,
                                                                                      'categ_product_retail':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_retail'] + product.lst_price,
                                                                                      'categ_product_sale_ly':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_sale_ly'] + (
                                                                                                  ly_product_product_count * product.lst_price),
                                                                                      'categ_product_sale_lly':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_sale_lly'] + (
                                                                                                  product.lst_price * lly_product_product_count),
                                                                                      'categ_product_invoice_amount':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                      'categ_product_cost_amount':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_cost_amount'] + product_cost_amount,
                                                                                      'categ_gross_margin':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_gross_margin'] + gross_margin,
                                                                                      'categ_dts':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_dts'] + dts,
                                                                                      'categ_gmroi':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_gmroi'] + gmroi,
                                                                                      'categ_turn':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_turn'] + turn,
                                                                                      'categ_shown':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_shown'] + shown,
                                                                                      'categ_product_old_onhand_qty':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                      'categ_product_old_onhand_cost':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                      'categ_ly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                      'categ_lly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                      'categ_product_current_unit':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_current_unit'] + product_current_unit,
                                                                                      'categ_product_current_cost':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_product_current_cost'] + product_current_cost,
                                                                                      'categ_days_on_hand':
                                                                                          total_categ_dict[
                                                                                              child_category.id][
                                                                                              'categ_days_on_hand'] + days_on_hand}})
                                                        total_categ_dict.update({category.id:
                                                                                     {'categ_product_count':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_count'] + product_product_count,
                                                                                      'categ_product_retail':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_retail'] + product.lst_price,
                                                                                      'categ_product_sale_ly':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_sale_ly'] + (
                                                                                                  ly_product_product_count * product.lst_price),
                                                                                      'categ_product_sale_lly':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_sale_lly'] + (
                                                                                                  product.lst_price * lly_product_product_count),
                                                                                      'categ_product_invoice_amount':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                      'categ_product_cost_amount':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_cost_amount'] + product_cost_amount,
                                                                                      'categ_gross_margin':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_gross_margin'] + gross_margin,
                                                                                      'categ_dts':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_dts'] + dts,
                                                                                      'categ_gmroi':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_gmroi'] + gmroi,
                                                                                      'categ_turn':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_turn'] + turn,
                                                                                      'categ_shown':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_shown'] + shown,
                                                                                      'categ_product_old_onhand_qty':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                      'categ_product_old_onhand_cost':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                      'categ_ly_product_product_count':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                      'categ_lly_product_product_count':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                      'categ_product_current_unit':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_current_unit'] + product_current_unit,
                                                                                      'categ_product_current_cost':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_product_current_cost'] + product_current_cost,
                                                                                      'categ_days_on_hand':
                                                                                          total_categ_dict[category.id][
                                                                                              'categ_days_on_hand'] + days_on_hand}})
                                                        total_categ_dict.update({sub_category.id:
                                                                                     {'categ_product_count':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_count'] + product_product_count,
                                                                                      'categ_product_retail':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_retail'] + product.lst_price,
                                                                                      'categ_product_sale_ly':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_sale_ly'] + (
                                                                                                  ly_product_product_count * product.lst_price),
                                                                                      'categ_product_sale_lly':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_sale_lly'] + (
                                                                                                  product.lst_price * lly_product_product_count),
                                                                                      'categ_product_invoice_amount':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                      'categ_product_cost_amount':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_cost_amount'] + product_cost_amount,
                                                                                      'categ_gross_margin':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_gross_margin'] + gross_margin,
                                                                                      'categ_dts':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_dts'] + dts,
                                                                                      'categ_gmroi':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_gmroi'] + gmroi,
                                                                                      'categ_turn':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_turn'] + turn,
                                                                                      'categ_shown':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_shown'] + shown,
                                                                                      'categ_product_old_onhand_qty':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                      'categ_product_old_onhand_cost':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                      'categ_ly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                      'categ_lly_product_product_count':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                      'categ_product_current_unit':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_current_unit'] + product_current_unit,
                                                                                      'categ_product_current_cost':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_product_current_cost'] + product_current_cost,
                                                                                      'categ_days_on_hand':
                                                                                          total_categ_dict[
                                                                                              sub_category.id][
                                                                                              'categ_days_on_hand'] + days_on_hand}})
                                                        total_categ_dict.update({parent_categ.id:
                                                            {
                                                                # 'categ_product_count':
                                                                #  total_categ_dict[
                                                                #      parent_categ.id][
                                                                #      'categ_product_count'] + product_product_count,
                                                                # 'categ_product_retail':
                                                                #     total_categ_dict[
                                                                #         parent_categ.id][
                                                                #         'categ_product_retail'] + product.lst_price,
                                                                'categ_product_sale_ly':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_sale_ly'] + (
                                                                            ly_product_product_count * product.lst_price),
                                                                'categ_product_sale_lly':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_sale_lly'] + (
                                                                            product.lst_price * lly_product_product_count),
                                                                'categ_product_invoice_amount':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_invoice_amount'] + product_invoice_amount,
                                                                # 'categ_product_cost_amount':
                                                                #     total_categ_dict[
                                                                #         parent_categ.id][
                                                                #         'categ_product_cost_amount'] + product_cost_amount,
                                                                'categ_gross_margin':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_gross_margin'] + gross_margin,
                                                                'categ_dts':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_dts'] + dts,
                                                                'categ_gmroi':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_gmroi'] + gmroi,
                                                                'categ_turn':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_turn'] + turn,
                                                                'categ_shown':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_shown'] + shown,
                                                                'categ_product_old_onhand_qty':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                'categ_product_old_onhand_cost':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                'categ_ly_product_product_count':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_ly_product_product_count'] + ly_product_product_count,
                                                                'categ_lly_product_product_count':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_lly_product_product_count'] + lly_product_product_count,
                                                                'categ_product_current_unit':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_current_unit'] + product_current_unit,
                                                                'categ_product_current_cost':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_product_current_cost'] + product_current_cost,
                                                                'categ_days_on_hand':
                                                                    total_categ_dict[
                                                                        parent_categ.id][
                                                                        'categ_days_on_hand'] + days_on_hand}})

                                                if stop_current_execution:
                                                    continue

                                                lines.append({
                                                    'id': line_id,
                                                    'name': product_name,
                                                    'unfoldable': False,
                                                    'class': 'vendor_int',
                                                    'columns': column,
                                                    'level': product_line_level,

                                                })

                                                line_id += 1
                                            else:
                                                for line in sn_sp_all:
                                                    for key, val in line.items():
                                                        if key == product.id and len(val[0]) > 1:
                                                            for data in val[0]:
                                                                for period in periods:
                                                                    period_date_from = period.get('date_from')
                                                                    period_date_to = period.get('date_to')

                                                                    product_sale_amount_list = self.get_sale_amount_for_lot(
                                                                        period_date_from,
                                                                        period_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                                        period_date_from,
                                                                        period_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    product_sale_amount_list[0] = \
                                                                        product_sale_amount_list[0] + \
                                                                        product_sale_amount_list_pos[
                                                                            0]
                                                                    product_sale_amount_list[1] = \
                                                                        product_sale_amount_list[1] + \
                                                                        product_sale_amount_list_pos[
                                                                            1]
                                                                    product_sale_amount_list[2] = \
                                                                        product_sale_amount_list[2] + \
                                                                        product_sale_amount_list_pos[
                                                                            2]
                                                                    product_sale_amount_list[3] = \
                                                                        product_sale_amount_list[3] + \
                                                                        product_sale_amount_list_pos[
                                                                            3]

                                                                    product_cost_amount = product_sale_amount_list[0]
                                                                    product_invoice_amount = product_sale_amount_list[1]
                                                                    product_retail_sale = product_sale_amount_list[2]
                                                                    product_product_count = product_sale_amount_list[3]
                                                                    if not product_product_count:
                                                                        stop_current_execution = True
                                                                        break

                                                                    avg_count = product_sale_amount_list[4] + \
                                                                                product_sale_amount_list_pos[4]

                                                                    # last year data
                                                                    ly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                                        last_yr_date_from,
                                                                        last_yr_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    ly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                                        last_yr_date_from,
                                                                        last_yr_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    ly_product_sale_amount_list[3] = \
                                                                        ly_product_sale_amount_list[
                                                                            3] + \
                                                                        ly_product_sale_amount_list_pos[
                                                                            3]

                                                                    ly_product_product_count = \
                                                                        ly_product_sale_amount_list[3]

                                                                    # last last year data
                                                                    lly_product_sale_amount_list = self.get_sale_amount_for_lot(
                                                                        lly_date_from, lly_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    lly_product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                                        lly_date_from,
                                                                        lly_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    lly_product_sale_amount_list[3] = \
                                                                        lly_product_sale_amount_list[
                                                                            3] + \
                                                                        lly_product_sale_amount_list_pos[
                                                                            3]

                                                                    lly_product_product_count = \
                                                                        lly_product_sale_amount_list[3]

                                                                    product_onhand_product_history = self.get_onhand_product_history_for_lot(
                                                                        period_date_to,
                                                                        product_id=product.id, lot=data)
                                                                    product_old_onhand_qty, product_old_onhand_cost = product_onhand_product_history

                                                                    if period_date_from == date_from:
                                                                        product_list = self.get_onhand_product_for_lot(
                                                                            product=product, lot=data)
                                                                        onhand_product_cost_amount = product_list[
                                                                                                         2] or 0
                                                                        sale_purchase_perc = 0
                                                                        if category_product_total and product_product_count:
                                                                            sale_purchase_perc = product_product_count / (
                                                                                category_product_total)
                                                                        sale_purchase_perc_sum += onhand_product_cost_amount
                                                                        sale_purchase_perc = str(
                                                                            self.format_value(
                                                                                round(sale_purchase_perc * 100,
                                                                                      2))) + '%'

                                                                        product_perc = total_invoice_amount and product_invoice_amount / total_invoice_amount or 0
                                                                        product_sale_perc = str(
                                                                            self.format_value(
                                                                                round(product_perc * 100, 2))) + '%'
                                                                        sale_perc_sum += product_perc
                                                                        column = [
                                                                            {
                                                                                'name': product.default_code and product.default_code or ''},
                                                                            {'name': '', 'class': 'text-left'},
                                                                            {'name': owner},
                                                                            {'name': ''},
                                                                            {'name': product_sale_perc},
                                                                            {'name': sale_purchase_perc},
                                                                            {'name': int(product_product_count)},
                                                                            {'name': self.dollar_format_value(
                                                                                product.lst_price)},
                                                                            # {'name': (self.format_value(product.lst_price)*product_product_count) },
                                                                            # {'name': product_cost_amount },
                                                                            # {'name': 0.0 },
                                                                            # {'name': 0.0 ,'style':'border-right:1px solid black;'},
                                                                            # {'name': self.format_value(product_old_onhand_qty)},
                                                                            # {'name': self.format_value(product_old_onhand_cost),'style':'border-right:1px solid black;'},
                                                                            # {'name': self.format_value(ly_product_product_count) },
                                                                            # {'name': self.format_value(product.lst_price * ly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                                            # {'name': self.format_value(lly_product_product_count) },
                                                                            # {'name': self.format_value(product.lst_price * lly_product_product_count) ,'style':'border-right:1px solid black;'},
                                                                            # {'name': 0.0 },
                                                                            # {'name': 0.0 },
                                                                            # {'name': 0.0 },
                                                                            # {'name': 0.0 },
                                                                            # {'name':owner},
                                                                            # {'name':product_name},
                                                                            # {'name':self.get_vendor_reference(product)},
                                                                            # {'name':self.format_value(product.lst_price)},
                                                                            # {'name':product_product_count},
                                                                            # {'name':product_sale_perc},
                                                                            # {'name':sale_purchase_perc},
                                                                            # {'name':'0.00'}
                                                                        ]
                                                                        retail_sum += (product.lst_price * int(
                                                                            product_product_count))

                                                                    invoice_sale_sum[
                                                                        period_date_from] += product_invoice_amount
                                                                    product_count_sum[
                                                                        period_date_from] += product_product_count
                                                                    retail_sale_sum[
                                                                        period_date_from] += product_retail_sale
                                                                    product_invoice_amount_formatted = self.dollar_format_value(
                                                                        product_invoice_amount)
                                                                    product_discount = product_retail_sale and (
                                                                            product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                                                    # column += [
                                                                    # 	{'name':product_invoice_amount_formatted},
                                                                    # 	{'name':product_discount_perc}
                                                                    # 	]
                                                                    if period_date_from == date_from:
                                                                        average_sale = product_product_count and product_invoice_amount / product_product_count or 0
                                                                        gross_margin = product_invoice_amount - product_cost_amount
                                                                        gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                                                        product_cost_sum += product_cost_amount
                                                                        gross_margin_sum += gross_margin

                                                                        product_cost_amount_dol = product_cost_amount
                                                                        gross_margin_dol = gross_margin

                                                                        gross_margin_perc = str(
                                                                            self.format_value(
                                                                                round(gross_margin_perc * 100,
                                                                                      2))) + '%'

                                                                        current_inventory = self.get_current_inventory_for_lot(
                                                                            product=product, lot=data)
                                                                        product_current_unit = current_inventory[0]
                                                                        product_current_cost = current_inventory[1]
                                                                        dts = self.get_dts_data_for_lot(
                                                                            period_date_from,
                                                                            period_date_to,
                                                                            product=product,
                                                                            lot=data)

                                                                        # aged_inventory = total_values_cost and (product_current_cost / total_values_cost) * 100

                                                                        days_on_hand = self.get_day_on_hand_for_lot(
                                                                            product=product,
                                                                            lot=data)
                                                                        shown = self.get_crm_shown(period_date_from,
                                                                                                   period_date_to,
                                                                                                   product=product)
                                                                        avg_cost = avg_count and product_cost_amount_dol / avg_count or 0

                                                                        gmroi = avg_cost and gross_margin_dol / avg_cost or 0
                                                                        turn = avg_cost and product_cost_amount_dol / avg_cost or 0
                                                                        column += [
                                                                            {'name': product_invoice_amount_formatted},
                                                                            {'name': self.dollar_format_value(
                                                                                product_cost_amount)},
                                                                            {'name': self.dollar_format_value(
                                                                                gross_margin)},
                                                                            {'name': gross_margin_perc},
                                                                            {'name': int(
                                                                                dts / product_product_count if product_product_count else 0)},
                                                                            {'name': self.format_value(
                                                                                gmroi / product_product_count if product_product_count else 0)},
                                                                            {'name': self.format_value(
                                                                                turn / product_product_count if product_product_count else 0)},
                                                                            {'name': int(shown)},
                                                                            {'name': int(ly_product_product_count),
                                                                             'class': 'border-left  number'},
                                                                            {'name': self.dollar_format_value(
                                                                                product.lst_price * ly_product_product_count)},
                                                                            {'name': int(lly_product_product_count),
                                                                             'class': 'border-left  number'},
                                                                            {'name': self.dollar_format_value(
                                                                                product.lst_price * lly_product_product_count)},
                                                                            {'name': int(product_current_unit),
                                                                             'class': 'border-left  number'},
                                                                            {'name': self.dollar_format_value(
                                                                                product_current_cost)},
                                                                            # {'name': self.format_value(aged_inventory) + '%'},
                                                                            {'name': int(
                                                                                days_on_hand / product_product_count if product_product_count else 0)},
                                                                        ]

                                                                        if len(val[1]) == 1:
                                                                            column[3].update({'name': val[1][0]})
                                                                        if len(val[1]) > 1:
                                                                            column[3].update({'name': ",".join(val[1])})
                                                                        column[1].update({'name': data})
                                                                        # for line in sn_sp_all[0]:
                                                                        # 	for key, val in line.items():
                                                                        # 		if key == product.id and len(val)==1:
                                                                        # 			column[1].update({'name': val[0]})
                                                                        # for line in sn_sp_all[1]:
                                                                        # 	for key, val in line.items():
                                                                        # 		if key == product.id and len(val)==1:
                                                                        # 			column[3].update({'name': val[0]})

                                                                        product_list = self.get_onhand_product_for_lot(
                                                                            product=product, lot=data)
                                                                        product_available_qty = product_list[0]
                                                                        product_available_product_price = product_list[
                                                                            1]
                                                                        product_available_qty_perc = total_qty_available and product_available_qty / total_qty_available or 0
                                                                        product_avg_on_hand_price = product_available_qty and product_available_product_price / product_available_qty or 0

                                                                        product_available_qty_sum += product_available_qty
                                                                        product_available_qty_perc_sum += product_available_qty_perc
                                                                        product_available_product_price_sum += product_available_product_price
                                                                        product_avg_on_hand_price_sum += product_avg_on_hand_price

                                                                        total_gmroi += gmroi
                                                                        total_turn += turn
                                                                        total_shown += shown
                                                                        total_dts += dts
                                                                        total_period_oh += product_old_onhand_qty
                                                                        total_period_cogs += product_old_onhand_cost
                                                                        total_ly_units += ly_product_product_count
                                                                        total_ly_amnt += (
                                                                                product.lst_price * ly_product_product_count)

                                                                        total_lly_units += lly_product_product_count
                                                                        total_lly_amnt += (
                                                                                product.lst_price * lly_product_product_count)

                                                                        invt_unit += product_current_unit
                                                                        invt_cost += product_current_cost
                                                                        # invt_aged += aged_inventory
                                                                        invt_doh += days_on_hand
                                                                        total_categ_dict.update({child_category.id:
                                                                            {
                                                                                'categ_product_count':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_count'] + product_product_count,
                                                                                'categ_product_retail':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_retail'] + product.lst_price,
                                                                                'categ_product_sale_ly':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_sale_ly'] + (
                                                                                            ly_product_product_count * product.lst_price),
                                                                                'categ_product_sale_lly':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_sale_lly'] + (
                                                                                            product.lst_price * lly_product_product_count),
                                                                                'categ_product_invoice_amount':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                'categ_product_cost_amount':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_cost_amount'] + product_cost_amount,
                                                                                'categ_gross_margin':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_gross_margin'] + gross_margin,
                                                                                'categ_dts':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_dts'] + dts,
                                                                                'categ_gmroi':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_gmroi'] + gmroi,
                                                                                'categ_turn':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_turn'] + turn,
                                                                                'categ_shown':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_shown'] + shown,
                                                                                'categ_product_old_onhand_qty':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                'categ_product_old_onhand_cost':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                'categ_ly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                'categ_lly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                'categ_product_current_unit':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_current_unit'] + product_current_unit,
                                                                                'categ_product_current_cost':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_product_current_cost'] + product_current_cost,
                                                                                'categ_days_on_hand':
                                                                                    total_categ_dict[
                                                                                        child_category.id][
                                                                                        'categ_days_on_hand'] + days_on_hand}})
                                                                        total_categ_dict.update({category.id:
                                                                            {
                                                                                'categ_product_count':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_count'] + product_product_count,
                                                                                'categ_product_retail':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_retail'] + product.lst_price,
                                                                                'categ_product_sale_ly':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_sale_ly'] + (
                                                                                            ly_product_product_count * product.lst_price),
                                                                                'categ_product_sale_lly':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_sale_lly'] + (
                                                                                            product.lst_price * lly_product_product_count),
                                                                                'categ_product_invoice_amount':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                'categ_product_cost_amount':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_cost_amount'] + product_cost_amount,
                                                                                'categ_gross_margin':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_gross_margin'] + gross_margin,
                                                                                'categ_dts':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_dts'] + dts,
                                                                                'categ_gmroi':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_gmroi'] + gmroi,
                                                                                'categ_turn':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_turn'] + turn,
                                                                                'categ_shown':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_shown'] + shown,
                                                                                'categ_product_old_onhand_qty':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                'categ_product_old_onhand_cost':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                'categ_ly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                'categ_lly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                'categ_product_current_unit':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_current_unit'] + product_current_unit,
                                                                                'categ_product_current_cost':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_product_current_cost'] + product_current_cost,
                                                                                'categ_days_on_hand':
                                                                                    total_categ_dict[
                                                                                        category.id][
                                                                                        'categ_days_on_hand'] + days_on_hand}})
                                                                        total_categ_dict.update({sub_category.id:
                                                                            {
                                                                                'categ_product_count':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_count'] + product_product_count,
                                                                                'categ_product_retail':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_retail'] + product.lst_price,
                                                                                'categ_product_sale_ly':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_sale_ly'] + (
                                                                                            ly_product_product_count * product.lst_price),
                                                                                'categ_product_sale_lly':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_sale_lly'] + (
                                                                                            product.lst_price * lly_product_product_count),
                                                                                'categ_product_invoice_amount':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                'categ_product_cost_amount':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_cost_amount'] + product_cost_amount,
                                                                                'categ_gross_margin':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_gross_margin'] + gross_margin,
                                                                                'categ_dts':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_dts'] + dts,
                                                                                'categ_gmroi':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_gmroi'] + gmroi,
                                                                                'categ_turn':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_turn'] + turn,
                                                                                'categ_shown':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_shown'] + shown,
                                                                                'categ_product_old_onhand_qty':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                'categ_product_old_onhand_cost':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                'categ_ly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                'categ_lly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                'categ_product_current_unit':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_current_unit'] + product_current_unit,
                                                                                'categ_product_current_cost':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_product_current_cost'] + product_current_cost,
                                                                                'categ_days_on_hand':
                                                                                    total_categ_dict[
                                                                                        sub_category.id][
                                                                                        'categ_days_on_hand'] + days_on_hand}})
                                                                        total_categ_dict.update({parent_categ.id:
                                                                            {
                                                                                # 'categ_product_count':
                                                                                #     total_categ_dict[
                                                                                #         parent_categ.id][
                                                                                #         'categ_product_count'] + product_product_count,
                                                                                # 'categ_product_retail':
                                                                                #     total_categ_dict[
                                                                                #         parent_categ.id][
                                                                                #         'categ_product_retail'] + product.lst_price,
                                                                                'categ_product_sale_ly':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_sale_ly'] + (
                                                                                            ly_product_product_count * product.lst_price),
                                                                                'categ_product_sale_lly':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_sale_lly'] + (
                                                                                            product.lst_price * lly_product_product_count),
                                                                                'categ_product_invoice_amount':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_invoice_amount'] + product_invoice_amount,
                                                                                # 'categ_product_cost_amount':
                                                                                #     total_categ_dict[
                                                                                #         parent_categ.id][
                                                                                #         'categ_product_cost_amount'] + product_cost_amount,
                                                                                'categ_gross_margin':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_gross_margin'] + gross_margin,
                                                                                'categ_dts':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_dts'] + dts,
                                                                                'categ_gmroi':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_gmroi'] + gmroi,
                                                                                'categ_turn':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_turn'] + turn,
                                                                                'categ_shown':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_shown'] + shown,
                                                                                'categ_product_old_onhand_qty':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_old_onhand_qty'] + product_old_onhand_qty,
                                                                                'categ_product_old_onhand_cost':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_old_onhand_cost'] + product_old_onhand_cost,
                                                                                'categ_ly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_ly_product_product_count'] + ly_product_product_count,
                                                                                'categ_lly_product_product_count':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_lly_product_product_count'] + lly_product_product_count,
                                                                                'categ_product_current_unit':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_current_unit'] + product_current_unit,
                                                                                'categ_product_current_cost':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_product_current_cost'] + product_current_cost,
                                                                                'categ_days_on_hand':
                                                                                    total_categ_dict[
                                                                                        parent_categ.id][
                                                                                        'categ_days_on_hand'] + days_on_hand}})

                                                                if stop_current_execution:
                                                                    continue

                                                                lines.append({
                                                                    'id': line_id,
                                                                    'name': product_name,
                                                                    'unfoldable': False,
                                                                    'class': 'vendor_int',
                                                                    'columns': column,
                                                                    'level': product_line_level,

                                                                })

                                                                line_id += 1
                                        categ_gross_margin_perc = total_categ_dict[child_category.id][
                                                                      'categ_product_invoice_amount'] and \
                                                                  total_categ_dict[child_category.id][
                                                                      'categ_gross_margin'] / \
                                                                  total_categ_dict[child_category.id][
                                                                      'categ_product_invoice_amount'] or 0
                                        categ_column = [
                                            {'name': ''},
                                            {'name': ''},
                                            {'name': ''},
                                            {'name': ''},
                                            {'name': ''},
                                            {'name': ''},
                                            {'name': int(total_categ_dict[child_category.id]['categ_product_count'])},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_product_retail'])},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_product_invoice_amount'])},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_product_cost_amount'])},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_gross_margin'])},
                                            {'name': str(
                                                self.format_value(round(categ_gross_margin_perc * 100, 2))) + '%'},
                                            {'name': int(total_categ_dict[child_category.id]['categ_dts'] /
                                                         total_categ_dict[child_category.id][
                                                             'categ_product_count'] if
                                                         total_categ_dict[child_category.id][
                                                             'categ_product_count'] else 0)},
                                            {'name': self.format_value(
                                                total_categ_dict[child_category.id]['categ_gmroi'] /
                                                total_categ_dict[child_category.id][
                                                    'categ_product_count'] if total_categ_dict[child_category.id][
                                                    'categ_product_count'] else 0)},
                                            {'name': self.format_value(
                                                total_categ_dict[child_category.id]['categ_turn'] /
                                                total_categ_dict[child_category.id][
                                                    'categ_product_count'] if total_categ_dict[child_category.id][
                                                    'categ_product_count'] else 0)},
                                            {'name': int(total_categ_dict[child_category.id]['categ_shown'])},
                                            {'name': int(
                                                total_categ_dict[child_category.id]['categ_ly_product_product_count']),
                                                'class': 'border-left  number'},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_product_sale_ly'])},
                                            {'name': int(
                                                total_categ_dict[child_category.id]['categ_lly_product_product_count']),
                                                'class': 'border-left  number'},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_product_sale_lly'])},
                                            {'name': int(
                                                total_categ_dict[child_category.id]['categ_product_current_unit']),
                                                'class': 'border-left  number'},
                                            {'name': self.dollar_format_value(
                                                total_categ_dict[child_category.id]['categ_product_current_cost'])},
                                            {'name': int(
                                                total_categ_dict[child_category.id]['categ_days_on_hand'] /
                                                total_categ_dict[child_category.id][
                                                    'categ_product_count'] if total_categ_dict[child_category.id][
                                                    'categ_product_count'] else 0)}, ]
                                        lines.append({
                                            'id': child_category_line_id,
                                            'name': child_category.complete_name,
                                            'unfoldable': False,
                                            'class': 'o_account_reports_level1',
                                            'title_hover': _('category'),
                                            'level': category_level,
                                            'columns': categ_column
                                        })
                            # categ_gross_margin_perc = total_categ_dict[category.id][
                            #                               'categ_product_invoice_amount'] and \
                            #                           total_categ_dict[category.id]['categ_gross_margin'] / \
                            #                           total_categ_dict[category.id][
                            #                               'categ_product_invoice_amount'] or 0
                            # categ_column = [
                            #     {'name': ''},
                            #     {'name': ''},
                            #     {'name': ''},
                            #     {'name': ''},
                            #     {'name': ''},
                            #     {'name': ''},
                            #     {'name': ''},
                            #     {'name': int(total_categ_dict[category.id]['categ_product_count'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_retail'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_invoice_amount'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_cost_amount'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_gross_margin'])},
                            #     {'name': str(self.format_value(round(categ_gross_margin_perc * 100, 2))) + '%'},
                            #     {'name': int(total_categ_dict[category.id]['categ_dts'] /
                            #                  total_categ_dict[category.id][
                            #                      'categ_product_count'] if total_categ_dict[category.id][
                            #         'categ_product_count'] else 0)},
                            #     {'name': self.format_value(
                            #         total_categ_dict[category.id]['categ_gmroi'] /
                            #         total_categ_dict[category.id][
                            #             'categ_product_count'] if total_categ_dict[category.id][
                            #             'categ_product_count'] else 0)},
                            #     {'name': self.format_value(
                            #         total_categ_dict[category.id]['categ_turn'] /
                            #         total_categ_dict[category.id][
                            #             'categ_product_count'] if total_categ_dict[category.id][
                            #             'categ_product_count'] else 0)},
                            #     {'name': int(total_categ_dict[category.id]['categ_shown'])},
                            #     {'name': int(total_categ_dict[category.id]['categ_product_old_onhand_qty'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_old_onhand_cost'])},
                            #     {'name': int(total_categ_dict[category.id]['categ_ly_product_product_count'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_sale_ly'])},
                            #     {'name': int(total_categ_dict[category.id]['categ_lly_product_product_count'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_sale_lly'])},
                            #     {'name': int(total_categ_dict[category.id]['categ_product_current_unit'])},
                            #     {'name': self.dollar_format_value(
                            #         total_categ_dict[category.id]['categ_product_current_cost'])},
                            #     {'name': int(
                            #         total_categ_dict[category.id]['categ_days_on_hand'] /
                            #         total_categ_dict[category.id][
                            #             'categ_product_count'] if total_categ_dict[category.id][
                            #             'categ_product_count'] else 0)}, ]
                            # lines.append({
                            #     'id': line_id,
                            #     'name': _('Sub Category Total 5'),
                            #     'unfoldable': False,
                            #     'columns': categ_column,
                            #     'level': category_total_level,
                            # })
                            # line_id += 1
                    # categ_gross_margin_perc = total_categ_dict[sub_category.id][
                    #                               'categ_product_invoice_amount'] and \
                    #                           total_categ_dict[sub_category.id]['categ_gross_margin'] / \
                    #                           total_categ_dict[sub_category.id][
                    #                               'categ_product_invoice_amount'] or 0
                    # categ_column = [
                    #     {'name': ''},
                    #     {'name': ''},
                    #     {'name': ''},
                    #     {'name': ''},
                    #     {'name': ''},
                    #     {'name': ''},
                    #     {'name': ''},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_product_count'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_retail'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_invoice_amount'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_cost_amount'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_gross_margin'])},
                    #     {'name': str(self.format_value(round(categ_gross_margin_perc * 100, 2))) + '%'},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_dts'] /
                    #                  total_categ_dict[sub_category.id][
                    #                      'categ_product_count'] if total_categ_dict[sub_category.id][
                    #         'categ_product_count'] else 0)},
                    #     {'name': self.format_value(
                    #         total_categ_dict[sub_category.id]['categ_gmroi'] /
                    #         total_categ_dict[sub_category.id][
                    #             'categ_product_count'] if total_categ_dict[sub_category.id][
                    #             'categ_product_count'] else 0)},
                    #     {'name': self.format_value(
                    #         total_categ_dict[sub_category.id]['categ_turn'] /
                    #         total_categ_dict[sub_category.id][
                    #             'categ_product_count'] if total_categ_dict[sub_category.id][
                    #             'categ_product_count'] else 0)},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_shown'])},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_product_old_onhand_qty'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_old_onhand_cost'])},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_ly_product_product_count'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_sale_ly'])},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_lly_product_product_count'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_sale_lly'])},
                    #     {'name': int(total_categ_dict[sub_category.id]['categ_product_current_unit'])},
                    #     {'name': self.dollar_format_value(
                    #         total_categ_dict[sub_category.id]['categ_product_current_cost'])},
                    #     {'name': int(
                    #         total_categ_dict[sub_category.id]['categ_days_on_hand'] /
                    #         total_categ_dict[sub_category.id][
                    #             'categ_product_count'] if total_categ_dict[sub_category.id][
                    #             'categ_product_count'] else 0)}, ]
                    # lines.append({
                    #     'id': line_id,
                    #     'name': _('Sub Category Total 6'),
                    #     'unfoldable': False,
                    #     'columns': categ_column,
                    #     'level': category_total_level,
                    # })
                    # line_id += 1
            categ_gross_margin_perc = total_categ_dict[parent_categ.id]['categ_product_invoice_amount'] and \
                                      total_categ_dict[parent_categ.id]['categ_gross_margin'] / \
                                      total_categ_dict[parent_categ.id]['categ_product_invoice_amount'] or 0
            categ_column = [
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                # KeyError: 'categ_product_retail'
                # {'name': int(total_categ_dict[parent_categ.id]['categ_product_count'])},
                # {'name': self.dollar_format_value(total_categ_dict[parent_categ.id]['categ_product_retail'])},
                {'name': self.dollar_format_value(
                    total_categ_dict[parent_categ.id]['categ_product_invoice_amount'])},
                # {'name': self.dollar_format_value(
                #     total_categ_dict[parent_categ.id]['categ_product_cost_amount'])},
                {'name': self.dollar_format_value(total_categ_dict[parent_categ.id]['categ_gross_margin'])},
                {'name': str(self.format_value(round(categ_gross_margin_perc * 100, 2))) + '%'},
                # KeyError: 'categ_product_count'
                # {'name': int(total_categ_dict[parent_categ.id]['categ_dts'] / total_categ_dict[parent_categ.id][
                #     'categ_product_count'] if total_categ_dict[parent_categ.id]['categ_product_count'] else 0)},
                # {'name': self.format_value(
                #     total_categ_dict[parent_categ.id]['categ_gmroi'] / total_categ_dict[parent_categ.id][
                #         'categ_product_count'] if total_categ_dict[parent_categ.id]['categ_product_count'] else 0)},
                # {'name': self.format_value(
                #     total_categ_dict[parent_categ.id]['categ_turn'] / total_categ_dict[parent_categ.id][
                #         'categ_product_count'] if total_categ_dict[parent_categ.id]['categ_product_count'] else 0)},
                {'name': int(total_categ_dict[parent_categ.id]['categ_shown'])},
                {'name': int(total_categ_dict[parent_categ.id]['categ_ly_product_product_count']),
                 'class': 'border-left  number'},
                {'name': self.dollar_format_value(total_categ_dict[parent_categ.id]['categ_product_sale_ly'])},
                {'name': int(total_categ_dict[parent_categ.id]['categ_lly_product_product_count']),
                 'class': 'border-left  number'},
                {'name': self.dollar_format_value(total_categ_dict[parent_categ.id]['categ_product_sale_lly'])},
                {'name': int(total_categ_dict[parent_categ.id]['categ_product_current_unit']),
                 'class': 'border-left  number'},
                {'name': self.dollar_format_value(
                    total_categ_dict[parent_categ.id]['categ_product_current_cost'])},
                # {'name': int(
                #     total_categ_dict[parent_categ.id]['categ_days_on_hand'] / total_categ_dict[parent_categ.id][
                #         'categ_product_count'] if total_categ_dict[parent_categ.id][
                #         'categ_product_count'] else 0)},
            ]
            lines.append({
                'id': parent_categ_line_id,
                'name': parent_categ.complete_name,
                'unfoldable': False,
                'class': 'o_account_reports_level1',
                'title_hover': _('category'),
                'columns': categ_column,
                'level': 1
            })

        # for line in sn_sp_all[0]:
        # 	for key, val in line.items():
        # 		if key == product.id and len(val)>1:
        # 			for data in val:
        # 				lines.append({
        # 					'id': line_id,
        # 					'name': product.default_code and product.default_code or '',
        # 					'unfoldable': False,
        # 					'class' : 'vendor_int',
        # 					'columns': [
        # 						{'name': data },
        # 					],
        # 					'level': 3,
        # 				})
        # 			line_id += 1

        # available_serial_numbers = product.get_available_serial_numbers(date_from, date_to)
        # if len(available_serial_numbers) > 0:
        # 	for av_ser in available_serial_numbers:
        # 		serial_sale_data = product.get_serial_numbers_sale_data(av_ser)
        # 		serial_dis = ((product.list_price - serial_sale_data[2]) / product.list_price) * 100
        # 		serial_gm = serial_sale_data[2] - serial_sale_data[1]
        # 		serial_gm_per = (serial_gm / serial_sale_data[2]) * 100
        # 		owner = 'O'
        # 		if serial_sale_data[3]:
        # 			owner ='M'

        # 		lines.append({
        # 			'id': line_id,
        # 			'name': _(''),
        # 			'unfoldable': False,
        # 			'columns': [

        # 				{'name':owner},{'name':serial_sale_data[0]},{'name':''},{'name':''},{'name':''},{'name':''},{'name':''},
        # 				{'name': str(self.format_value(serial_dis)) + '%'},
        # 				# {'name':self.format_value(product.list_price)},
        # 				{'name':self.format_value(serial_sale_data[2])},
        # 				{'name':'0.00'},

        # 				{'name':self.format_value(serial_sale_data[1])},
        # 				{'name':self.format_value(serial_gm)},
        # 				{'name':str( self.format_value(serial_gm_per) ) + '%'},
        # 				],
        # 			'title_hover': _('level 4'),
        # 			'level': 4,
        # 		})
        # Total Row
        onhand_product_cost_amount = 0
        if not sale_purchase_perc_sum + product_cost_sum == 0:
            onhand_product_cost_amount = product_cost_sum and product_cost_sum / (
                    sale_purchase_perc_sum + product_cost_sum) or 0
        sale_purchase_perc_sum = str(self.format_value(round(onhand_product_cost_amount * 100, 2))) + '%'
        sale_perc_sum_perc = str(self.format_value(round(sale_perc_sum * 100, 2))) + '%'

        bottom_column = [
            {'name': ''},
            {'name': ''},
            {'name': ''},
            {'name': ''},
            {'name': ''},
            {'name': ''},
            {'name': int(product_count_sum[period_date_from])},
            {'name': self.dollar_format_value(retail_sum)},
        ]
        # iterate with periods
        periods = self.remove_duplicated_period(periods)

        for period in periods:
            period_date_from = period.get('date_from')

            discount_sum = retail_sale_sum[period_date_from] and (
                    retail_sale_sum[period_date_from] - invoice_sale_sum[period_date_from]) / retail_sale_sum[
                               period_date_from] or 0
            discount_sum_perc = str(self.format_value(round(discount_sum * 100, 2))) + '%'

            bottom_column += [{'name': self.dollar_format_value(invoice_sale_sum[period_date_from])}]
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

                average_sale_sum = self.dollar_format_value(average_sale_sum)
                product_cost_sum = self.dollar_format_value(product_cost_sum)
                gross_margin_sum = self.dollar_format_value(gross_margin_sum)
                gross_margin_perc_sum = str(self.format_value(round(gross_margin_perc_sum * 100, 2))) + '%'
                product_available_qty_sum = self.format_value(product_available_qty_sum)
                product_available_product_price_sum = self.format_value(product_available_product_price_sum)

                bottom_column += [
                    {'name': product_cost_sum},
                    {'name': gross_margin_sum},
                    {'name': gross_margin_perc_sum},
                    {'name': int(total_dts / product_count_sum[period_date_from]) if product_count_sum[
                        period_date_from] else 0},

                    {'name': self.format_value(total_gmroi / product_count_sum[period_date_from] if product_count_sum[
                        period_date_from] else 0)},
                    {'name': self.format_value(total_turn / product_count_sum[period_date_from] if product_count_sum[
                        period_date_from] else 0)},
                    {'name': int(total_shown)},

                    {'name': int(total_ly_units)},
                    {'name': self.dollar_format_value(total_ly_amnt)},

                    {'name': int(total_lly_units)},
                    {'name': self.dollar_format_value(total_lly_amnt)},

                    {'name': int(invt_unit)},
                    {'name': self.dollar_format_value(invt_cost)},
                    # {'name': self.format_value(invt_aged)},
                    {'name': int(
                        invt_doh / product_count_sum[period_date_from] if product_count_sum[period_date_from] else 0)},
                ]
            # [{'name':'0.00'}, {'name':discount_sum_perc},{'name': sale_perc_sum_perc},
            # 					{'name': sale_purchase_perc_sum},
            # 					{'name':average_sale_sum},]

        lines.append({
            'id': line_id,
            'name': _('Total'),
            'unfoldable': False,
            'columns': bottom_column,
            'level': 1,
        })
        lines = sorted(lines, key=lambda x: x['id'])
        return [(0, line) for line in lines]

    def remove_duplicated_period(self, periods):
        seen = set()
        new_periods = []
        for d in periods:
            t = tuple(d.items())
            if t not in seen:
                seen.add(t)
                new_periods.append(d)

        return new_periods
