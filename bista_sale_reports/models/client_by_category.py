# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import pytz

from odoo import models, fields


class ClientByCategoryCustomHandler(models.AbstractModel):
    _name = 'client.by.category.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Client By Category Custom Handler'

    # def _custom_options_initializer(self, report, options, previous_options=None):
    #     # Remove multi-currency columns if needed
    #     super()._custom_options_initializer(report, options, previous_options=previous_options)
    #
    #     options['category'] = True

    def get_category_ids(self, date_from, date_to, salesperson_ids, category_ids):
        context = self.env.context
        new_category_ids = []
        category_ids = category_ids

        if not category_ids:
            category_ids = self.env['product.category'].search([('display_name', '!=', None)]).ids

        if category_ids:
            # generate category object
            category_ids = self.env['product.category'].browse(category_ids)

            for category_id in category_ids:
                new_category_ids.append(category_id.id)

            new_category_ids = list(set(new_category_ids))
            new_category_ids_str = ','.join(str(x) for x in new_category_ids)
            new_category_ids = '(' + new_category_ids_str + ')'

        sql = ("""
            SELECT sum(invoice_price) as category_sum, ss.category_id as category 
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
                    ,pc.id as category_id
               FROM pos_order_line pol
                    INNER JOIN pos_order po ON (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    INNER JOIN stock_picking_type spt ON (spt.id = sp.picking_type_id)
                    INNER JOIN stock_move sm ON (sp.id = sm.picking_id)
                    INNER JOIN res_partner rp ON (rp.id = po.partner_id)
                    INNER JOIN product_product pp ON (sm.product_id = pp.id)
                    INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                    INNER JOIN product_category pc ON (pc.id = pt.categ_id)
                    INNER JOIN hr_employee he on (he.id = po.employee_id) 
                WHERE sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('outgoing','incoming') 
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pt.exclude_FROM_report !=True 
                Group by pc.id
            )
            UNION
            (
                SELECT 
                    sum(case when sol.discount = 0.0 then (sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                            ELSE 0
                       END) else ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                            ELSE 0
                       END)* (sol.discount))/100.0 end) as invoice_price 
                    ,pc.id as category_id
                FROM sale_order_line sol
                    INNER JOIN sale_order so ON (so.id = sol.order_id)
                    INNER JOIN stock_picking sp ON (sp.group_id = so.procurement_group_id)
                    INNER JOIN stock_picking_type spt ON (spt.id = sp.picking_type_id)
                    INNER JOIN stock_move sm ON (sp.id = sm.picking_id)
                    INNER JOIN res_partner rp ON (rp.id = so.partner_id)
                    INNER JOIN product_product pp ON (sol.product_id = pp.id)
                    INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                    INNER JOIN product_category pc ON (pc.id = pt.categ_id) 
                WHERE sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code in ('outgoing','incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id 
                    and pt.exclude_FROM_report!=True 
                    and so.user_id in %s 
                Group by pc.id
            ))
             ss where category_id in %s group by category_id order by category_sum desc
        """) % (date_from, date_to, salesperson_ids, date_from, date_to, salesperson_ids, new_category_ids)
        self._cr.execute(sql)
        res = self._cr.fetchall()
        new_category_ids = []
        for id in res:
            new_category_ids.append(id[1])
        return new_category_ids

    def get_customer_ids(self, date_from, date_to, salesperson_ids, category_id):
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
                    INNER JOIN hr_employee he on (he.id = po.employee_id)
                WHERE sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('outgoing','incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pc.id =%s 
                    and pt.exclude_FROM_report!=True 
                group by rp.id
            )
            UNION
            (
                SELECT 
                    sum(case when sol.discount = 0.0 then (sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                            ELSE 0
                       END) else ((sol.price_unit*CASE 
                        WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                            ELSE 0
                       END)* (sol.discount))/100.0 end) as invoice_price 
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
                WHERE sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code in ('outgoing','incoming')
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_FROM_report!=True 
                    and pc.id = %s 
                    and so.user_id in %s 
                group by rp.id
            )) ss 
            group by partner_id order by customer_sum desc
        """) % (date_from, date_to, salesperson_ids, category_id, date_from, date_to, category_id, salesperson_ids)
        self._cr.execute(sql)
        res = self._cr.fetchall()
        customer_ids = []
        for id in res:
            customer_ids.append(id[1])
        return customer_ids

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
    # function for calculate sales amount based on the inputs given
    # ===========================================================================
    def get_sale_amount(self, date_from, date_to, salesperson_ids, category_id=None, customer_id=None):
        user_clause = ''
        if customer_id:
            user_clause = ',so.user_id as user_id'

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
                    
                ,sum(case when sol.discount = 0.0 then (sol.price_unit * 
                    CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) 
                         WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) 
                         ELSE 0 END) 
                    else 
                    ((sol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) 
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) * (sol.discount))/100.0 end) as invoice_price
                
                --,sum(sol.price_subtotal) as invoice_price
                   
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
                    END)* (sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else 
                    (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                        ELSE 0
                    END) end)  as gross_margin
                    
                    %s
                    
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('outgoing','incoming')
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and so.user_id in %s
                    and pt.exclude_from_report!=True
                """) % (user_clause, date_from, date_to, salesperson_ids)
        if category_id:
            sql += (' and (pc.id = %s or pc.parent_id = %s)' % (category_id, category_id))
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
            sql += (' group by pc.id, so.id')

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        invoice_sale = 0
        retail_sale = 0
        product_count = 0
        user_ids = []
        for value in result:
            invoice_sale += value.get('invoice_price', 0) or 0
            retail_sale += value.get('sale_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            if value.get('user_id', False):
                user_ids.append(value.get('user_id', 0))
        if customer_id:
            return invoice_sale, retail_sale, product_count, user_ids
        else:
            return invoice_sale, retail_sale, product_count

    def get_sale_amount_of_pos(self, date_from, date_to, salesperson_ids, category_id=None, customer_id=None):
        user_clause = ''
        if customer_id:
            user_clause = ',po.user_id as user_id'

        sql = ("""
        select 
            SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) as net_qty 
            ,sum(case when pt.list_price = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) else (pt.list_price* CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) end) as sale_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) else ((pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)  ELSE 0 END)* (pol.discount))/100.0 end) as invoice_price_1, sum(pol.price_subtotal) as invoice_price
            ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty) WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as gross_margin
            %s
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id) and sm.state !='cancel'
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
            inner join hr_employee he on (he.id = po.employee_id)
            inner join pos_order_res_users_rel porur on (po.id = porur.pos_order_id)
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing','incoming')
            and sm.state='done' 
            and sm.product_id = pol.product_id
            and he.user_id in %s 
            and pt.exclude_from_report !=True
            and porur.res_users_id in %s
        """) % (user_clause, date_from, date_to, salesperson_ids, salesperson_ids)
        if category_id:
            sql += (' and (pc.id = %s or pc.parent_id = %s)' % (category_id, category_id))
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
            sql += (' group by pc.id, po.id')

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        invoice_sale = 0
        retail_sale = 0
        product_count = 0
        user_ids = []
        for value in result:
            invoice_sale += value.get('invoice_price', 0) or 0
            retail_sale += value.get('sale_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            if value.get('user_id', False):
                user_ids.append(value.get('user_id', 0))
        if customer_id:
            return invoice_sale, retail_sale, product_count, user_ids
        else:
            return invoice_sale, retail_sale, product_count

    # ===========================================================================
    # Function for format amount with 2 decimal & grouping is based on the language settings
    # ===========================================================================
    def format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(
            fmt, value, grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'\u2011')
        return formatted_amount

    # ===========================================================================
    # Function to split emails into multiple lines if more than one email id is exists
    # ===========================================================================

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

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = []
        context = self.env.context
        line_id = 0

        date_from = context.get('date_from', False)
        if not date_from:
            if options.get('date') and options['date'].get('date_from'):
                date_from = options['date']['date_from']

        date_to = context.get('date_to', False)
        if not date_to:
            if options.get('date'):
                date_to = options['date'].get('date_to') or options['date'].get('date')

        periods = options['comparison'].get('periods')
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        salesperson_ids = options.get('users_ids', [])

        if salesperson_ids:
            salesperson_ids = salesperson_ids

        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
            salesperson_ids = salesperson_ids.ids

        salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
        salesperson_ids = '(' + salesperson_ids_str + ')'

        if date_from:
            date_from = str(date_from) + ' 00:00:00'
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        # called function to find the total sale for the period
        total_invoice_sale, total_discount, total_product_count = self.get_sale_amount(date_from, date_to,
                                                                                       salesperson_ids)
        total_invoice_sale_pos, total_discount_pos, total_product_count_pos = self.get_sale_amount_of_pos(date_from,
                                                                                                          date_to,
                                                                                                          salesperson_ids)
        total_invoice_sale = total_invoice_sale + total_invoice_sale_pos
        sale_perc_sum = 0
        sale_perc_sums = 0
        invoice_sale_sum = {}
        product_count_sum = {}
        retail_sale_sum = {}

        current_period_customer_ids = []
        current_category_invoice_sale = 0

        periods = self.remove_duplicated_period(periods)

        # initialize dictionary variable with zero based on periods
        for period in periods:
            period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
            invoice_sale_sum[period_date_from] = 0
            product_count_sum[period_date_from] = 0
            retail_sale_sum[period_date_from] = 0

        # Get all available categories and append to "category_ids_dict" dictionary
        category_ids = options.get('category_ids')
        category_ids_sorted = self.get_category_ids(date_from, date_to, salesperson_ids, category_ids)

        for category in self.env['product.category'].browse(category_ids_sorted):
            column = []
            for period in periods:

                period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
                period_date_to = self.get_date_with_tz(str(period.get('date_to')) + ' 23:59:59')

                # called function to get category wise sum and category wise customer details
                category_invoice_sale, category_retail_sale, category_product_count = self.get_sale_amount(
                    period_date_from, period_date_to, salesperson_ids, category_id=category.id)
                category_invoice_sale_pos, category_retail_sale_pos, category_product_count_pos = self.get_sale_amount_of_pos(
                    period_date_from, period_date_to, salesperson_ids, category_id=category.id)

                category_invoice_sale = category_invoice_sale + category_invoice_sale_pos
                category_retail_sale = category_retail_sale + category_retail_sale_pos
                category_product_count = category_product_count + category_product_count_pos

                category_discount = category_retail_sale and (category_retail_sale - category_invoice_sale) / category_retail_sale or 0
                invoice_sale_sum[period_date_from] += category_invoice_sale
                product_count_sum[period_date_from] += category_product_count
                retail_sale_sum[period_date_from] += category_retail_sale

                if period_date_from == date_from:
                    current_period_customer_ids = self.get_customer_ids(date_from, date_to, salesperson_ids, category.id)
                    category_perc = total_invoice_sale and category_invoice_sale / total_invoice_sale or 0
                    category_sale_perc = str(self.format_value(round(category_perc * 100, 2))) + '%'

                    sale_perc_sum += category_perc

                    current_category_invoice_sale = category_invoice_sale
                    category_invoice_sale = self.format_value(category_invoice_sale)
                    category_discount_perc = str(self.format_value(round(category_discount * 100, 2))) + '%'
                    column = [{'name': category_invoice_sale}, {'name': category_sale_perc},
                              {'name': category_product_count}, {'name': category_discount_perc},
                              {'name': ''},
                              {'name': ''},
                              {'name': ''},
                              ]
                else:
                    category_invoice_sale = self.format_value(category_invoice_sale)
                    category_discount_perc = str(self.format_value(round(category_discount * 100, 2))) + '%'
                    category_invoice_sale = category_invoice_sale.replace(',','')
                    category_invoice_sale = float(category_invoice_sale)
                    category_perc = total_invoice_sale and category_invoice_sale / total_invoice_sale or 0
                    sale_perc_sums += category_perc
                    category_sale_perc = str(self.format_value(round(category_perc * 100, 2))) + '%'
                    column += [{'name': category_invoice_sale}, {'name': category_sale_perc},
                               {'name': category_product_count},{'name': category_discount_perc},
                               {'name': ''},
                               {'name': ''},
                               {'name': ''},
                               ]
            address_column = [
                {'name': ''},
                {'name': ''},
                {'name': ''},
            ]
            lines.append({
                'id': line_id,
                'name': category.name_get()[0][1],
                'unfoldable': False,
                'columns': column,
                'level': 1,
            })
            line_id += 1

            for customer in self.env['res.partner'].browse(current_period_customer_ids):
                column = []
                customer_user_ids = []
                stop_current_execution = False
                for period in periods:

                    period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
                    period_date_to = self.get_date_with_tz(str(period.get('date_to')) + ' 23:59:59')

                    # called function to get customer wise sales details
                    (customer_invoice_sale, customer_retail_sale, customer_product_count,
                     so_user_ids) = self.get_sale_amount(period_date_from, period_date_to, salesperson_ids, category_id=category.id, customer_id=customer.id)

                    (category_invoice_sale_pos, category_retail_sale_pos, category_product_count_pos,
                     pos_user_ids) = self.get_sale_amount_of_pos(period_date_from, period_date_to, salesperson_ids, category_id=category.id, customer_id=customer.id)

                    customer_invoice_sale = customer_invoice_sale + category_invoice_sale_pos
                    customer_retail_sale = customer_retail_sale + category_retail_sale_pos
                    customer_product_count = customer_product_count + category_product_count_pos

                    customer_discount = customer_retail_sale and (
                            customer_retail_sale - customer_invoice_sale) / customer_retail_sale or 0
                    if period_date_from == date_from:
                        if not customer_invoice_sale:
                            stop_current_execution = True
                            break
                        customer_user_ids = list(set(so_user_ids + pos_user_ids))
                        contact_address, contact_address1, = self._get_address_details(customer)
                        salesperson_names_str = ', '.join(
                            str(user.name) for user in self.env['res.users'].browse(customer_user_ids))

                        customer_perc = customer_invoice_sale and customer_invoice_sale / current_category_invoice_sale or 0
                        customer_sale_perc = str(round(customer_perc * 100, 2)) + '%'
                        customer_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                        customer_invoice_sale = self.format_value(customer_invoice_sale)
                        column = [{'name': customer_invoice_sale}, {'name': customer_sale_perc},
                                  {'name': customer_product_count}, {'name': customer_discount_perc},
                                  {'name': contact_address}, {'name': contact_address1},
                                  {'name': salesperson_names_str or ''},
                                  ]
                    else:
                        customer_invoice_sale = self.format_value(customer_invoice_sale)
                        customer_invoice_sale = customer_invoice_sale.replace(',', '')
                        customer_invoice_sale = float(customer_invoice_sale)
                        customer_perc = customer_invoice_sale and customer_invoice_sale / current_category_invoice_sale or 0
                        customer_sale_perc = str(round(customer_perc * 100, 2)) + '%'
                        customer_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                        contact_address, contact_address1, = self._get_address_details(customer)
                        salesperson_names_str = ', '.join(
                            str(user.name) for user in self.env['res.users'].browse(customer_user_ids))
                        column += [{'name': customer_invoice_sale},{'name': customer_sale_perc},
                                   {'name': customer_product_count},
                                   {'name': customer_discount_perc},{'name': contact_address}, {'name': contact_address1},
                                  {'name': salesperson_names_str or ''},]

                # contact_address = ''
                # if customer.street:
                #     contact_address += customer.street + ' , '
                # if customer.city:
                #     contact_address += customer.city + ', '
                # if customer.state_id:
                #     contact_address += customer.state_id.name
                # if customer.zip:
                #     contact_address += ' ' + customer.zip
                #
                # contact_address1 = customer.phone or ''
                # if contact_address1 and customer.mobile:
                #     contact_address1 += '/ ' + customer.mobile
                # elif customer.mobile:
                #     contact_address1 = customer.mobile
                # if contact_address1:
                #     contact_address1 += ' , '
                # if customer.email:
                #     contact_address1 += self.split_multi_emails(customer.email, ';')
                if stop_current_execution:
                    continue
                # salesperson_names_str = ''
                # if customer_user_ids:
                #     salesperson_names_str = ', '.join(
                #         str(user.name) for user in self.env['res.users'].browse(customer_user_ids))

                # address_column = [{'name': contact_address}, {'name': contact_address1},
                #                   {'name': salesperson_names_str or ''}]
                lines.append({
                    'id': line_id,
                    'name': customer.name,
                    'type': 'line',
                    'unfoldable': False,
                    'columns': column,
                    'level': 3,
                })
                line_id += 1

        # Total Row
        sale_perc_sum_perc = str(self.format_value(round(sale_perc_sum * 100, 2))) + '%'
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
                bottom_column += [
                    {'name': self.format_value(invoice_sale_sum[period_date_from])},
                    {'name': sale_perc_sum_perc},
                    {'name': product_count_sum[period_date_from]},
                    {'name': discount_sum_perc},{'name': ''}, {'name': ''},{'name': ''}]
            else:
                sales_perc_sum_perc = str(self.format_value(round(sale_perc_sums * 100, 2))) + '%'
                bottom_column += [
                    {'name': self.format_value(invoice_sale_sum[period_date_from])},
                    {'name': sales_perc_sum_perc},
                    {'name': product_count_sum[period_date_from]},
                    {'name': discount_sum_perc},{'name': ''}, {'name': ''},{'name': ''}]
        # address_column = [
        #     {'name': ''},
        #     {'name': ''},
        #     {'name': ''},
        # ]

        lines.append({
            'id': line_id,
            'name': 'Total',
            'unfoldable': False,
            'columns': bottom_column ,
            'level': 1,
        })

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
