# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import pytz

from odoo import models, fields, _
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class ClientRankingCustomHandler(models.AbstractModel):
    _name = 'client.ranking.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Client Ranking Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        # Remove multi-currency columns if needed
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if 'order_type' not in previous_options:
            options['order_type'] = [
                {'id': 'Ascending', 'name': _('Ascending'), 'selected': True},
                {'id': 'Descending', 'name': _('Descending'), 'selected': False}
            ]
        else:
            options['order_type'] = previous_options['order_type']

        if 'details' not in previous_options:
            options['details'] = [
                {'id': 'No Details', 'name': _('No Details'), 'selected': True},
                {'id': 'Vendor Name', 'name': _('Vendor Name'), 'selected': False},
                {'id': 'Product Sku', 'name': _('Product Sku'), 'selected': False}
            ]
        else:
            options['details'] = previous_options['details']

        if 'customer_limit' not in previous_options:
            options['customer_limit'] = {'limit': 100}
        else:
            options['customer_limit'] = previous_options['customer_limit']

    # ===========================================================================
    # Function for add timezone with given date
    # ===========================================================================
    def get_date_with_tz(self, date):
        datetime_with_tz = pytz.timezone(
            self._context['tz']).localize(fields.Datetime.from_string(date), is_dst=None)  # No daylight saving time
        datetime_in_utc = datetime_with_tz.astimezone(pytz.utc)
        date = datetime_in_utc.strftime('%Y-%m-%d %H:%M:%S')
        return date

    # ===========================================================================
    # function for calculate sales amount based on the inputs given
    # ===========================================================================
    def get_sale_amount(self, date_from, date_to, salesperson_ids, customer_id=None, product_id=None, vendor_id=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = (""" inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id) """)
        user_clause = ''
        if customer_id:
            user_clause = ',so.user_id as user_id '
        sql = ("""
            select
                SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) as net_qty
                ,sum(case when pt.list_price = 0.0 then (sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) else (pt.list_price* CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) end) as sale_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) else ((sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END)* (sol.discount))/100.0 end) as invoice_price
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) end) as cost_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) else ((sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END)* (sol.discount))/100.0 end - case 
                        when pp.std_price= 0.0 then 0 else (pp.std_price * CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) end)  as gross_margin
                %s
            from sale_order_line sol
                inner join sale_order so on (so.id = sol.order_id)
                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                inner join stock_move sm on (sp.id = sm.picking_id) and sm.state !='cancel'
                inner join res_partner rp on (rp.id = so.partner_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id)
                %s
            where sp.date_done >= '%s' and sp.date_done <= '%s'
                and sp.state = 'done' 
                and spt.code in ('outgoing', 'incoming') 
                and sm.product_id = sol.product_id 
                and so.user_id in %s
        """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.name = %s ') % (str(vendor_id))

        if product_id:
            sql += (' and sol.product_id = %s ') % (product_id)
            # if customer id is given, add customer filter with domain
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
            # sql += (' group by so.user_id')
        sql += ' GROUP BY so.user_id'
        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        invoice_sale = sum(value.get('invoice_price', 0) or 0 for value in result)
        retail_sale = sum(value.get('sale_price', 0) or 0 for value in result)
        product_count = sum(value.get('net_qty', 0) or 0 for value in result)
        user_ids = [value.get('user_id', 0) for value in result if value.get('user_id', False)]

        # Return results
        if customer_id:
            return invoice_sale, retail_sale, product_count, user_ids
        else:
            return invoice_sale, retail_sale, product_count

    def get_sale_amount_of_pos(self, date_from, date_to, salesperson_ids, customer_id=None, product_id=None,
                               vendor_id=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = ("""
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                """)
        user_clause = ''
        if customer_id:
            user_clause = ',he.user_id as user_id'
        sql = ("""
            select 
                SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) as net_qty
                ,sum(case when pt.list_price = 0.0 then (pol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) else (pt.list_price* CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) end) as sale_price
                ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) else ((pol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END)* (pol.discount))/100.0 end) as invoice_price 
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) end) as cost_price
                ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                   END) else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case 
                        when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) 
                        as gross_margin
                %s
            from pos_order_line pol
                inner join pos_order po on (po.id = pol.order_id)
                inner join stock_picking sp on (sp.pos_order_id = po.id)
                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                inner join stock_move sm on (sp.id = sm.picking_id)
                inner join res_partner rp on (rp.id = po.partner_id)
                inner join product_product pp on (sm.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id)
                inner join hr_employee he on (he.id = po.employee_id) 
                %s
            where sp.date_done >= '%s' 
                and sp.date_done <= '%s'
                and sp.state = 'done' 
                and spt.code in ('outgoing', 'incoming') 
                and sm.product_id = pol.product_id 
                and he.user_id in %s
        """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += ('and psi.name = %s') % (str(vendor_id))
        if product_id:
            sql += (' and pol.product_id = %s ') % (product_id)
            # if customer id is given, add customer filter with domain
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
        sql += (' group by he.user_id')

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        invoice_sale = sum(value.get('invoice_price',0) or 0 for value in result)
        retail_sale = sum(value.get('sale_price',0) or 0 for value in result)
        product_count = sum(value.get('net_qty',0) or 0 for value in result)
        user_ids = [value.get('user_id',0) for value in result if value.get('user_id',False)]
        if customer_id:
            return invoice_sale, retail_sale, product_count, user_ids
        else:
            return invoice_sale, retail_sale, product_count

    def get_customer_ids(self, date_from, date_to, salesperson_ids, limit):
        context = self.env.context
        if context.get('sort_order', 'asc') == 'asc':
            order_by = 'order by customer_sum'
        else:
            order_by = 'order by customer_sum desc'

        customer_limit = ('limit %s') % (limit.get('limit', 50))
        sql = ("""
            SELECT sum(invoice_price) as customer_sum, ss.partner_id as partner_id
            FROM (
                (
                    SELECT
                        sum(case when pol.discount = 0.0 then (pol.price_unit*CASE 
                            WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                            ELSE 0
                        END) else ((pol.price_unit*CASE 
                            WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                            ELSE 0
                        END)* (pol.discount))/100.0 end) as invoice_price
                        ,rp.id as partner_id
                    FROM pos_order_line pol
                        INNER JOIN pos_order po ON (po.id = pol.order_id)
                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        INNER JOIN stock_picking_type spt ON (spt.id = sp.picking_type_id)
                        INNER JOIN stock_move sm ON (sp.id = sm.picking_id)
                        INNER JOIN res_partner rp ON (rp.id = po.partner_id)
                        INNER JOIN product_product pp ON (sm.product_id = pp.id)
                        INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                        INNER JOIN product_category pc ON (pc.id = pt.categ_id)
                        INNER JOIN product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                        INNER JOIN hr_employee he on (he.id = po.employee_id)
                    WHERE sp.date_done >= '%s' 
                           and sp.date_done <= '%s'
                           and sp.state = 'done' 
                           and spt.code in ('outgoing','incoming') 
                           and sm.product_id = pol.product_id
                           and he.user_id in %s 
                           and pt.exclude_FROM_report = False 
                        group by rp.id
                )
                UNION
                (
                SELECT
                    sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0 END) else ((sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0 END)* (sol.discount))/100.0 end) as invoice_price
                    ,rp.id as partner_id
                FROM sale_order_line sol
                    INNER JOIN sale_order so ON (so.id = sol.order_id)
                    INNER JOIN stock_picking sp ON (sp.group_id = so.procurement_group_id)
                    INNER JOIN stock_picking_type spt ON (spt.id = sp.picking_type_id)
                    INNER JOIN stock_move sm ON (sp.id = sm.picking_id)
                    INNER JOIN res_partner rp ON (rp.id = so.partner_id)
                    INNER JOIN product_product pp ON (sol.product_id = pp.id)
                    INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                    INNER JOIN product_category pc ON (pc.id = pt.categ_id)
                    INNER JOIN product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                WHERE sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('outgoing','incoming') 
                    and sm.product_id = sol.product_id
                    and pt.exclude_FROM_report = False 
                    and so.user_id in %s group by rp.id
                )
            ) ss 
            Group by partner_id %s %s 
        """) % (date_from, date_to, salesperson_ids, date_from, date_to, salesperson_ids, order_by, customer_limit)
        self._cr.execute(sql)
        res = self._cr.fetchall()
        customer_ids = []
        for id in res:
            customer_ids.append(id[1])
        return customer_ids

    # ========================================================================================
    # Function for format amount with 2 decimal & grouping is based on the language settings
    # ========================================================================================
    def format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(
            fmt, value, grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'\u2011')
        return formatted_amount

    # ================================================================================
    # Function to split emails into multiple lines if more than one email id is exists
    # ================================================================================
    def split_multi_emails(self, email, symbol):
        if symbol in email:
            email_list = email.split(symbol)
            email = ''
            for x in email_list:
                if not email:
                    email = x
                else:
                    email += ' , ' + x
        return email

    def get_product_details_of_customer(self, date_from, date_to, salesperson_ids, customer_id):
        vendor_ids = []
        sql = ("""
               select 
                   distinct psi.name as vendor_id
               from sale_order_line sol
                   inner join sale_order so on (so.id = sol.order_id)
                   inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                   inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                   inner join stock_move sm on (sp.id = sm.picking_id)
                   inner join product_product pp on (sol.product_id = pp.id)
                   inner join product_template pt on (pp.product_tmpl_id = pt.id)
                   inner join product_category pc on (pc.id = pt.categ_id) 
                   INNER JOIN product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
               where sp.date_done >= '%s' and sp.date_done <= '%s' 
                   and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                   and sm.product_id = sol.product_id and so.user_id in %s and so.partner_id=%s 
               """) % (date_from, date_to, salesperson_ids, customer_id)
        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            vendor_ids += id

        return vendor_ids

    def _get_address_details(self, customer):
        contact_address = ', '.join(filter(None, [customer.street, customer.city, customer.state_id.name])) + (
            ' - ' + customer.zip if customer.zip else '')

        contact_address1 = customer.phone or ''
        if contact_address1 and customer.mobile:
            contact_address1 += '/ ' + customer.mobile
        elif customer.mobile:
            contact_address1 = customer.mobile
        if customer.email:
            if not contact_address1:
                contact_address1 += self.split_multi_emails(customer.email, ';')
            else:
                contact_address1 += ' , ' + self.split_multi_emails(customer.email, ';')

        return contact_address, contact_address1

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = []
        limit = options.get('customer_limit', {'limit': 50})
        context = self.env.context
        line_id = 0
        date_from = context.get('date_from') or (options['date']['date_from'] if options.get('date') else False)
        date_to = context.get('date_to') or (options['date'].get('date_to') or options['date'].get('date') if options.get('date') else False)
        periods = options['comparison'].get('periods')
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}
        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)
        salesperson_ids = options.get('users_ids', [])

        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)]).ids
        salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
        salesperson_ids = '(' + salesperson_ids_str + ')'

        date_from = self.get_date_with_tz(date_from + ' 00:00:00') if date_from else False
        date_to = self.get_date_with_tz(date_to + ' 23:59:59') if date_to else False

        # called function to find the total sale for the period
        total_invoice_sale, total_discount, total_product_count, = self.get_sale_amount(date_from, date_to,
                                                                                        salesperson_ids)
        total_invoice_sale_pos, total_discount_pos, total_product_count_pos, = self.get_sale_amount_of_pos(date_from,
                                                                                                           date_to,
                                                                                                           salesperson_ids)
        total_invoice_sale += total_invoice_sale_pos
        customer_ids = self.get_customer_ids(date_from, date_to, salesperson_ids, limit)

        sale_perc_sum = 0
        sale_perc_sums = 0
        invoice_sale_sum = {self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00'): 0 for period in periods}
        product_count_sum = {self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00'): 0 for period in periods}
        retail_sale_sum = {self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00'): 0 for period in periods}
        current_customer_invoice_sale = 0
        periods = self.remove_duplicated_period(periods)
        # initialize dictionary variable with zero based on periods
        # iterate with customer ids
        for customer in self.env['res.partner'].browse(customer_ids):
            column = []
            customer_user_ids = []
            for period in periods:
                period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
                period_date_to = self.get_date_with_tz(str(period.get('date_to')) + ' 23:59:59')
                # called function to get customer wise sum and details
                (customer_invoice_sale, category_retail_sale, customer_product_count,
                 so_user_ids) = self.get_sale_amount(period_date_from, period_date_to,
                                                     salesperson_ids, customer_id=customer.id)
                (customer_invoice_sale_pos, category_retail_sale_pos, customer_product_count_pos,
                 pos_user_ids) = self.get_sale_amount_of_pos(period_date_from, period_date_to,
                                                             salesperson_ids, customer_id=customer.id)
                customer_invoice_sale +=  customer_invoice_sale_pos
                category_retail_sale += category_retail_sale_pos
                customer_product_count +=  customer_product_count_pos
                customer_discount = category_retail_sale and (category_retail_sale - customer_invoice_sale) / category_retail_sale or 0
                invoice_sale_sum[period_date_from] += customer_invoice_sale
                product_count_sum[period_date_from] += customer_product_count
                retail_sale_sum[period_date_from] += category_retail_sale
                if period_date_from == date_from:
                    customer_perc = total_invoice_sale and customer_invoice_sale / total_invoice_sale or 0
                    sale_perc_sum += customer_perc
                    customer_user_ids = so_user_ids + pos_user_ids
                    contact_address, contact_address1, = self._get_address_details(customer)

                    salesperson_names_str = ', '.join(
                        str(user.name) for user in self.env['res.users'].browse(customer_user_ids))

                    current_customer_invoice_sale = customer_invoice_sale
                    customer_sale_perc = str(self.format_value(round(customer_perc * 100, 2))) + '%'
                    customer_invoice_sale = self.format_value(customer_invoice_sale)
                    customer_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                    column += [
                                {'name': customer_invoice_sale}, {'name': customer_sale_perc},
                                {'name': customer_product_count},
                                {'name': customer_discount_perc},
                                {'name': contact_address}, {'name': contact_address1},
                                {'name': salesperson_names_str or ''},
                    ]
                else:
                    customer_user_ids = so_user_ids + pos_user_ids
                    contact_address, contact_address1, = self._get_address_details(customer)

                    salesperson_names_str = ', '.join(
                        str(user.name) for user in self.env['res.users'].browse(customer_user_ids))

                    customer_invoice_sale = self.format_value(customer_invoice_sale)
                    customer_invoice_sale = customer_invoice_sale.replace(',', '')
                    customer_invoice_sale = float(customer_invoice_sale)
                    customer_perc = total_invoice_sale and customer_invoice_sale / total_invoice_sale or 0
                    sale_perc_sums += customer_perc
                    customer_sale_perc = str(self.format_value(round(customer_perc * 100, 2))) + '%'
                    customer_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                    column += [{'name': customer_invoice_sale}, {'name': customer_sale_perc},{'name': customer_product_count},
                               {'name': customer_discount_perc},
                               {'name': contact_address}, {'name': contact_address1},
                               {'name': salesperson_names_str or ''},
                               ]
            lines.append({
                'id': line_id,
                'name': customer.name,
                'unfoldable': False,
                'columns': column,
                'level': 3,
            })
            line_id += 1
            # if more details needs to be shown, fetch ordered product details
            # if vendor wise details
            if context.get('view_type', 'no') != 'no':
                vendor_ids = self.get_product_details_of_customer(date_from, date_to, salesperson_ids, customer.id)
                for vendor_id in vendor_ids:
                    column = []
                    vendor_product_tmpl_ids = []
                    current_vendor_invoice_sale = 0
                    if context.get('view_type', 'no') == 'product':
                        sql = ("""
                                    SELECT 
                                        distinct psi.product_tmpl_id
                                    FROM res_partner rp 
                                        INNER JOIN product_supplierinfo psi on(rp.id = psi.name)
                                        INNER JOIN product_template pt ON (psi.product_tmpl_id = pt.id)
                                        INNER JOIN product_product pp ON (pp.product_tmpl_id = pt.id)
                                        INNER JOIN stock_move sm ON (pp.id = sm.product_id)
                                        INNER JOIN stock_picking sp ON (sp.id = sm.picking_id)
                                    WHERE rp.id= %s and sm.date >= '%s' and sm.date <= '%s' and sp.partner_id = %s
                                """) % (vendor_id, date_from, date_to, customer.id)
                        self._cr.execute(sql)
                        res = self._cr.fetchall()
                        for id in res:
                            vendor_product_tmpl_ids.append(id[0])

                    for period in periods:
                        period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
                        period_date_to = self.get_date_with_tz(str(period.get('date_to')) + ' 23:59:59')
                        # called function to get vendor wise sales details
                        vendor_invoice_sale, vender_retail_sale, vendor_product_count, vendor_customer_ids = self.get_sale_amount(
                            period_date_from, period_date_to, salesperson_ids, customer_id=customer.id,
                            vendor_id=vendor_id)
                        vendor_invoice_sale_pos, vender_retail_sale_pos, vendor_product_count_pos, vendor_customer_ids = self.get_sale_amount_of_pos(
                            period_date_from, period_date_to, salesperson_ids, customer_id=customer.id,
                            vendor_id=vendor_id)
                        vendor_invoice_sale +=  vendor_invoice_sale_pos
                        vender_retail_sale += vender_retail_sale_pos
                        vendor_product_count +=  vendor_product_count_pos

                        vendor_discount = vender_retail_sale and (
                                vender_retail_sale - vendor_invoice_sale) / vender_retail_sale or 0

                        if period_date_from == date_from:
                            vendor_perc = current_customer_invoice_sale and vendor_invoice_sale / current_customer_invoice_sale or 0
                            vendor_sale_perc = str(round(vendor_perc * 100, 2)) + '%'
                            current_vendor_invoice_sale = vendor_invoice_sale
                            vendor_discount_perc = str(self.format_value(round(vendor_discount * 100, 2))) + '%'
                            column += [{'name': vendor_invoice_sale}, {'name': vendor_sale_perc},
                                       {'name': vendor_product_count},
                                       {'name': vendor_discount_perc},
                                       ]
                        else:
                            vendor_discount_perc = str(self.format_value(round(vendor_discount * 100, 2))) + '%'
                            vendor_invoice_sale = self.format_value(vendor_invoice_sale)
                            column += [{'name': vendor_invoice_sale}, {'name': vendor_product_count},
                                       {'name': vendor_discount_perc},
                                       ]

                    address_column = [{'name': ' '}, {'name': ' '}, {'name': ' '}]

                    lines.append({
                        'id': line_id,
                        'name': self.env['res.partner'].browse(vendor_id).name,
                        'unfoldable': False,
                        'columns': column + address_column,
                        'level': 3,
                    })
                    line_id += 1
                    # if product SKU wise details
                    if context.get('view_type', 'no') == 'product':
                        vendor_product_tmpl_ids_str = ','.join(str(x) for x in vendor_product_tmpl_ids)
                        vendor_product_tmpl_ids = '(' + vendor_product_tmpl_ids_str + ')'
                        sql = ("""
                                    SELECT 
                                        distinct pp.id
                                    FROM product_product pp
                                        INNER JOIN stock_move sm ON (pp.id = sm.product_id) 
                                        INNER JOIN stock_picking sp ON (sp.id = sm.picking_id) 
                                        INNER JOIN product_supplierinfo psi on(pp.product_tmpl_id = psi.product_tmpl_id)
                                    WHERE pp.product_tmpl_id in %s and sm.date >= '%s' and sm.date <= '%s' and sp.partner_id = %s
                                        and psi.name = %s
                                """) % (vendor_product_tmpl_ids, date_from, date_to, customer.id, vendor_id)
                        self._cr.execute(sql)
                        res = self._cr.fetchall()
                        product_ids = []
                        for id in res:
                            product_ids.append(id[0])
                        for product_id in product_ids:
                            column = []
                            for period in periods:
                                period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
                                period_date_to = self.get_date_with_tz(str(period.get('date_to')) + ' 23:59:59')
                                # called function to get product wise sales details
                                product_invoice_sale, product_retail_sale, product_product_count, product_customer_ids = self.get_sale_amount(
                                    period_date_from, period_date_to, salesperson_ids, customer_id=customer.id,
                                    product_id=product_id, vendor_id=vendor_id)
                                product_invoice_sale_pos, product_retail_sale_pos, product_product_count_pos, product_customer_ids = self.get_sale_amount_of_pos(
                                    period_date_from, period_date_to, salesperson_ids, customer_id=customer.id,
                                    product_id=product_id, vendor_id=vendor_id)
                                product_invoice_sale = product_invoice_sale + product_invoice_sale_pos
                                product_retail_sale = product_retail_sale + product_retail_sale_pos
                                product_product_count = product_product_count + product_product_count_pos

                                product_discount = product_retail_sale and (
                                        product_retail_sale - product_invoice_sale) / product_retail_sale or 0

                                if period_date_from == date_from:
                                    product_perc = current_vendor_invoice_sale and product_invoice_sale / current_vendor_invoice_sale or 0
                                    product_sale_perc = str(round(product_perc * 100, 2)) + '%'
                                    product_discount_perc = str(
                                        self.format_value(round(product_discount * 100, 2))) + '%'
                                    product_invoice_sale = self.format_value(product_invoice_sale)
                                    column += [{'name': product_invoice_sale},
                                               {'name': product_sale_perc},
                                               {'name': product_product_count},
                                               {'name': product_discount_perc},
                                               ]
                                else:
                                    product_discount_perc = str(
                                        self.format_value(round(product_discount * 100, 2))) + '%'
                                    product_invoice_sale = self.format_value(product_invoice_sale)
                                    column += [{'name': product_invoice_sale}, {'name': product_product_count},
                                               {'name': product_discount_perc}]

                            address_column = [{'name': ' '}, {'name': ' '}, {'name': ' '}]
                            product = self.env['product.product'].browse(product_id)
                            lines.append({
                                'id': line_id,
                                'name': product.default_code or product.name,
                                'unfoldable': False,
                                'columns': column + address_column,
                                'level': 3,
                            })
                            line_id += 1

        # Total Row
        bottom_column = []
        periods = self.remove_duplicated_period(periods)
        # iterate with periods
        for period in periods:
            period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
            period_date_to = self.get_date_with_tz(str(period.get('date_to')) + ' 23:59:59')

            discount = retail_sale_sum[period_date_from] and (
                    retail_sale_sum[period_date_from] - invoice_sale_sum[period_date_from]) / retail_sale_sum[
                           period_date_from] or 0
            discount_sum_perc = str(self.format_value(round(discount * 100, 2))) + '%'
            if period_date_from == date_from:
                sale_perc_sum_perc = str(self.format_value(round(sale_perc_sum * 100, 2))) + '%'
                bottom_column += [{'name': self.format_value(invoice_sale_sum[period_date_from])},
                                  {'name': sale_perc_sum_perc},
                                  {'name': product_count_sum[period_date_from]}, {'name': discount_sum_perc},
                                  {'name': ''}, {'name': ''},{'name': ''}
                                  ]
            else:
                (customer_invoice_sale, category_retail_sale, customer_product_count,
                 so_user_ids) = self.get_sale_amount(period_date_from, period_date_to,
                                                     salesperson_ids, customer_id=customer.id)
                (customer_invoice_sale_pos, category_retail_sale_pos, customer_product_count_pos,
                 pos_user_ids) = self.get_sale_amount_of_pos(period_date_from, period_date_to,
                                                             salesperson_ids, customer_id=customer.id)
                customer_invoice_sale += customer_invoice_sale_pos
                customer_perc = total_invoice_sale and customer_invoice_sale / total_invoice_sale or 0

                sale_perc_sums += customer_perc
                sale_perc_sums_perc = str(self.format_value(round(sale_perc_sums * 100, 2))) + '%'
                bottom_column += [{'name': self.format_value(invoice_sale_sum[period_date_from])},
                                  {'name': sale_perc_sums_perc},
                                  {'name': product_count_sum[period_date_from]}, {'name': discount_sum_perc},
                                  {'name': ' '}, {'name': ' '}, {'name': ' '}
                                  ]

        address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
        lines.append({
            'id': line_id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': bottom_column ,
        })
        line_id += 1

        return [(0, line) for line in lines]

    def _query_values(self, report, options):
        """ Executes the queries, and performs all the computations.

        :return:    [(record, values_by_column_group), ...],  where
                    - record is an account.account record.
                    - values_by_column_group is a dict in the form {column_group_key: values, ...}
                        - column_group_key is a string identifying a column group, as in options['column_groups']
                        - values is a list of dictionaries, one per period containing:
                            - sum:                              {'debit': float, 'credit': float, 'balance': float}
                            - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                            - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
        """
        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(report, options)

        if not query:
            return []

        groupby_accounts = {}
        groupby_companies = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            column_group_key = res['column_group_key']
            key = res['key']
            if key == 'sum':
                groupby_accounts.setdefault(res['groupby'],
                                            {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res

            elif key == 'initial_balance':
                groupby_accounts.setdefault(res['groupby'],
                                            {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res

            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(res['groupby'],
                                             {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_companies[res['groupby']][column_group_key] = res

        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        if groupby_companies:
            candidates_account_ids = self.env['account.account']._name_search(options.get('filter_search_bar'), [
                ('account_type', '=', 'equity_unaffected'),
                ('company_id', 'in', list(groupby_companies.keys())),
            ])
            for account in self.env['account.account'].browse(candidates_account_ids):
                company_unaffected_earnings = groupby_companies.get(account.company_id.id)
                if not company_unaffected_earnings:
                    continue
                for column_group_key in options['column_groups']:
                    unaffected_earnings = company_unaffected_earnings[column_group_key]
                    groupby_accounts.setdefault(account.id,
                                                {col_group_key: {} for col_group_key in options['column_groups']})
                    groupby_accounts[account.id][column_group_key]['unaffected_earnings'] = unaffected_earnings
                del groupby_companies[account.company_id.id]

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.
        if groupby_accounts:
            accounts = self.env['account.account'].search([('id', 'in', list(groupby_accounts.keys()))])
        else:
            accounts = []

        return [(account, groupby_accounts[account.id]) for account in accounts]

    def _get_query_sums(self, report, options):
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :return:                    (query, params)
        """
        options_by_column_group = report._split_options_per_column_group(options)

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================
        for column_group_key, options_group in options_by_column_group.items():
            if not options.get('general_ledger_strict_range'):
                options_group = self._get_options_sum_balance(options_group)

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'normal'

            query_domain = []

            if options.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options['filter_search_bar']))

            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            tables, where_clause, where_params = report._query_get(options_group, sum_date_scope, domain=query_domain)
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id
            """)

            # ============================================
            # 2) Get sums for the unaffected earnings.
            # ============================================
            if not options_group.get('general_ledger_strict_range'):
                unaff_earnings_domain = [('account_id.include_initial_balance', '=', False)]

                # The period domain is expressed as:
                # [
                #   ('date' <= fiscalyear['date_from'] - 1),
                #   ('account_id.include_initial_balance', '=', False),
                # ]

                new_options = self._get_options_unaffected_earnings(options_group)
                tables, where_clause, where_params = report._query_get(new_options, 'strict_range',
                                                                       domain=unaff_earnings_domain)
                params.append(column_group_key)
                params += where_params
                queries.append(f"""
                    SELECT
                        account_move_line.company_id                            AS groupby,
                        'unaffected_earnings'                                   AS key,
                        NULL                                                    AS max_date,
                        %s                                                      AS column_group_key,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                        SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM {tables}
                    LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                    WHERE {where_clause}
                    GROUP BY account_move_line.company_id
                """)

        return ' UNION ALL '.join(queries), params

    def remove_duplicated_period(self, periods):
        seen = set()
        new_periods = []
        for d in periods:
            t = tuple(d.items())
            if t not in seen:
                seen.add(t)
                new_periods.append(d)
        return new_periods
