# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from collections import OrderedDict
from operator import itemgetter

import pytz

from odoo import models, fields


class ClientByPricePointCustomHandler(models.AbstractModel):
    _name = 'client.by.price.point.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Client By Price Point Custom Handler'

    # def _custom_options_initializer(self, report, options, previous_options=None):
    #     # Remove multi-currency columns if needed
    #     super()._custom_options_initializer(report, options, previous_options=previous_options)
    #     if not self.user_has_groups('base.group_multi_currency'):
    #         options['columns'] = [
    #             column for column in options['columns']
    #             if column['expression_label'] != 'amount_currency'
    #         ]
    #
    #     options['order_type'] = [{'id': 'Ascending', 'name': _('Ascending'), 'selected': False},
    #                              {'id': 'Descending', 'name': _('Descending'), 'selected': False}]
    #
    #     options['details'] = [{'id': 'No Details', 'name': _('No Details'), 'selected': False},
    #                           {'id': 'Vendor Name', 'name': _('Vendor Name'), 'selected': False},
    #                           {'id': 'Product Sku', 'name': _('Product Sku'), 'selected': False}]
    #
    #     options['customer_limit'] = {'limit': 50}
    #
    #     # Automatically unfold the report when printing it, unless some specific lines have been unfolded
    #     options['unfold_all'] = (self._context.get('print_mode') and not options.get('unfolded_lines')) or options[
    #         'unfold_all']

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
    def get_sale_amount(self, date_from, date_to, salesperson_ids, customer_id=None, order_id=None):
        context = self.env.context
        # get salesperson from context

        retail_sale = 0
        invoice_sale = 0
        product_count = 0
        if date_from:
            date_from = str(date_from) + ' 00:00:00'
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

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
               END)* (sol.discount))/100.0 end) as invoice_price 
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
               END)* (sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) end)  as gross_margin
            from sale_order_line sol
                inner join sale_order so on (so.id = sol.order_id)
                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                inner join stock_move sm on (sp.id = sm.picking_id)
                inner join res_partner rp on (rp.id = so.partner_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where sp.date_done >= '%s' and sp.date_done <= '%s' 
                and sp.state = 'done' and spt.code in ('outgoing','incoming') and sm.product_id = sol.product_id and so.user_id in %s
                and sm.state='done'
                and pt.exclude_from_report!=True
            """) % (date_from, date_to, salesperson_ids)

        if customer_id:
            sql += (' and so.partner_id=%s ' % (customer_id))
        if order_id:
            sql += (' and so.id=%s ' % (order_id))

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        retail_sale = 0
        invoice_sale = 0
        gross_margin = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0

        return invoice_sale, retail_sale, product_count

    def get_sale_amount_of_pos(self, date_from, date_to, salesperson_ids, customer_id=None, order_id=None):
        context = self.env.context
        # get salesperson from context

        retail_sale = 0
        invoice_sale = 0
        product_count = 0
        if date_from:
            date_from = str(date_from) + ' 00:00:00'
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

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
               END)* (pol.discount))/100.0 end) as invoice_price 
            ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin
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
        where sp.date_done >= '%s' and sp.date_done <= '%s'
            and sp.state = 'done' and spt.code in ('outgoing','incoming') and sm.product_id = pol.product_id
            and sm.state='done'
            and he.user_id in %s and pt.exclude_from_report!=True
        """) % (date_from, date_to, salesperson_ids)

        if customer_id:
            sql += ('and po.partner_id=%s ' % (customer_id))
        if order_id:
            sql += ('and po.id=%s ' % (order_id))

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        retail_sale = 0
        invoice_sale = 0
        gross_margin = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0

        return invoice_sale, retail_sale, product_count

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

    # ===========================================================================
    # Function to split emails into multiple lines if more than one email id is exists
    # ===========================================================================
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
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format.encode('UTF-8')
        lines = []
        context = self.env.context

        company_id = context.get('company_id') or self.env.user.company_id

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

        salesperson_ids = options.get('users_ids', [])

        if not salesperson_ids:
            salesperson_ids = salesperson_ids = self.env['res.users'].search(
                ['|', ('active', '=', False), ('active', '=', True)])
            salesperson_ids = salesperson_ids.ids

        salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
        salesperson_ids = '(' + salesperson_ids_str + ')'

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        # called function to find the total ssale for the period
        total_invoice_sale, total_discount, total_product_count = self.get_sale_amount(date_from, date_to,
                                                                                       salesperson_ids)
        total_invoice_sale_pos, total_discount_pos, total_product_count_pos = self.get_sale_amount_of_pos(date_from,
                                                                                                          date_to,
                                                                                                          salesperson_ids)
        total_invoice_sale = total_invoice_sale + total_invoice_sale_pos

        customer_ids = context.get('partner_ids', [])
        if not customer_ids:
            customer_ids = self.env['res.partner'].search([('customer_rank', '>', 0)])

        customer_ids = customer_ids.ids

        order_ids = []
        sql = ("""
                            select distinct so.id from sale_order so
                            inner join sale_order_line sol on (so.id = sol.order_id)
                            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join stock_move sm on (sp.id = sm.picking_id)
                            where sp.date_done >= '%s' and sp.date_done <= '%s' 
                            and sp.state = 'done' and spt.code in ('outgoing','incoming') and sm.product_id = sol.product_id and so.user_id in %s
                            """) % (date_from, date_to, salesperson_ids)
        if customer_ids:
            customer_ids_str = ','.join(str(x) for x in customer_ids)
            customer_ids = '(' + customer_ids_str + ')'
            sql += (' and so.partner_id in %s ' % (customer_ids))
        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            if id not in order_ids:
                order_ids += id

        pos_order_ids = []
        sql = ("""
                            select distinct po.id from pos_order po
                            inner join pos_order_line pol on (po.id = pol.order_id)

                            inner join stock_picking sp on (sp.pos_order_id = po.id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join stock_move sm on (sp.id = sm.picking_id)
                            inner join hr_employee he on (he.id = po.employee_id)
                            where sp.date_done >= '%s' and sp.date_done <= '%s'
                            and sp.state = 'done' and spt.code in ('outgoing','incoming') and sm.product_id = pol.product_id and he.user_id in %s
                            """) % (date_from, date_to, salesperson_ids)
        if customer_ids:
            sql += (' and po.partner_id in %s' % (customer_ids))
        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            if id not in pos_order_ids:
                pos_order_ids += id

        # initialize as ordered dict in order to maintian the key order as declared
        sale_order_price_range_dict = OrderedDict()

        sale_order_price_range_dict['100,000+'] = {}
        sale_order_price_range_dict['75,000-99,999'] = {}
        sale_order_price_range_dict['50,000-74,999'] = {}
        sale_order_price_range_dict['45,000-49,999'] = {}
        sale_order_price_range_dict['40,000-44,999'] = {}
        sale_order_price_range_dict['35,000-39,999'] = {}
        sale_order_price_range_dict['30,000-34,999'] = {}
        sale_order_price_range_dict['25,000-29,999'] = {}
        sale_order_price_range_dict['20,000-24,999'] = {}
        sale_order_price_range_dict['15,000-19,999'] = {}
        sale_order_price_range_dict['10,000-14,999'] = {}
        sale_order_price_range_dict['7,500-9,999'] = {}
        sale_order_price_range_dict['5,000-7,499'] = {}
        sale_order_price_range_dict['2,500-4,999'] = {}
        sale_order_price_range_dict['2,000-2,499'] = {}
        sale_order_price_range_dict['1,500-1,999'] = {}
        sale_order_price_range_dict['1,000-1,499'] = {}
        sale_order_price_range_dict['500-999'] = {}
        sale_order_price_range_dict['0-499'] = {}

        range_wise_invoice_total_dict = {
            '100,000+': {},
            '75,000-99,999': {},
            '50,000-74,999': {},
            '45,000-49,999': {},
            '40,000-44,999': {},
            '35,000-39,999': {},
            '30,000-34,999': {},
            '25,000-29,999': {},
            '20,000-24,999': {},
            '15,000-19,999': {},
            '10,000-14,999': {},
            '7,500-9,999': {},
            '5,000-7,499': {},
            '2,500-4,999': {},
            '2,000-2,499': {},
            '1,500-1,999': {},
            '1,000-1,499': {},
            '500-999': {},
            '0-499': {},
        }
        range_wise_discount_dict = {
            '100,000+': {},
            '75,000-99,999': {},
            '50,000-74,999': {},
            '45,000-49,999': {},
            '40,000-44,999': {},
            '35,000-39,999': {},
            '30,000-34,999': {},
            '25,000-29,999': {},
            '20,000-24,999': {},
            '15,000-19,999': {},
            '10,000-14,999': {},
            '7,500-9,999': {},
            '5,000-7,499': {},
            '2,500-4,999': {},
            '2,000-2,499': {},
            '1,500-1,999': {},
            '1,000-1,499': {},
            '500-999': {},
            '0-499': {},
        }
        range_wise_item_count_dict = {
            '100,000+': {},
            '75,000-99,999': {},
            '50,000-74,999': {},
            '45,000-49,999': {},
            '40,000-44,999': {},
            '35,000-39,999': {},
            '30,000-34,999': {},
            '25,000-29,999': {},
            '20,000-24,999': {},
            '15,000-19,999': {},
            '10,000-14,999': {},
            '7,500-9,999': {},
            '5,000-7,499': {},
            '2,500-4,999': {},
            '2,000-2,499': {},
            '1,500-1,999': {},
            '1,000-1,499': {},
            '500-999': {},
            '0-499': {},
        }
        periods = self.remove_duplicated_period(periods)
        # initialize dictionary variable with zero based on periods
        for period in periods:
            for key in range_wise_invoice_total_dict.keys():
                range_wise_invoice_total_dict[key][period.get('date_from')] = 0
                range_wise_discount_dict[key][period.get('date_from')] = 0
                range_wise_item_count_dict[key][period.get('date_from')] = 0

        def update_dict(key, order_id, period_date_from, customer_invoice_sale, customer_retail_sale,
                        customer_product_count):
            if period_date_from == date_from:
                sale_order_price_range_dict[key][order_id] = customer_invoice_sale
            range_wise_invoice_total_dict[key][period_date_from] += customer_invoice_sale[0]
            range_wise_discount_dict[key][period_date_from] += customer_retail_sale
            range_wise_item_count_dict[key][period_date_from] += customer_product_count
            return True

        for order in self.env['sale.order'].browse(order_ids):
            for period in periods:
                period_date_from = period.get('date_from')
                period_date_to = period.get('date_to')

                customer_invoice_sale, customer_retail_sale, customer_product_count = self.get_sale_amount(
                    period_date_from, period_date_to, salesperson_ids, order_id=order.id)
                customer_discount = customer_retail_sale and (
                        customer_retail_sale - customer_invoice_sale) / customer_retail_sale or 0
                if (customer_invoice_sale != 0 or customer_product_count != 0) and customer_invoice_sale <= 499:
                    update_dict('0-499', order.id, period_date_from,    [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 500 and customer_invoice_sale <= 999:
                    update_dict('500-999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 1000 and customer_invoice_sale <= 1499:
                    update_dict('1,000-1,499', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 1500 and customer_invoice_sale <= 1999:
                    update_dict('1,500-1,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 2000 and customer_invoice_sale <= 2499:
                    update_dict('2,000-2,499', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 2500 and customer_invoice_sale <= 4999:
                    update_dict('2,500-4,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 5000 and customer_invoice_sale <= 7499:
                    update_dict('5,000-7,499', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 7500 and customer_invoice_sale <= 9999:
                    update_dict('7,500-9,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 10000 and customer_invoice_sale <= 14999:
                    update_dict('10,000-14,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 15000 and customer_invoice_sale <= 19999:
                    update_dict('15,000-19,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 20000 and customer_invoice_sale <= 24999:
                    update_dict('20,000-24,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 25000 and customer_invoice_sale <= 29999:
                    update_dict('25,000-29,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 30000 and customer_invoice_sale <= 34999:
                    update_dict('30,000-34,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 35000 and customer_invoice_sale <= 39999:
                    update_dict('35,000-39,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 40000 and customer_invoice_sale <= 44999:
                    update_dict('40,000-44,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 45000 and customer_invoice_sale <= 49999:
                    update_dict('45,000-49,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 50000 and customer_invoice_sale <= 74999:
                    update_dict('50,000-74,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 75000 and customer_invoice_sale <= 99999:
                    update_dict('75,000-99,999', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 100000:
                    update_dict('100,000+', order.id, period_date_from, [customer_invoice_sale, 'sale'],
                                customer_retail_sale, customer_product_count)

        for order in self.env['pos.order'].browse(pos_order_ids):
            for period in periods:
                period_date_from = period.get('date_from')
                period_date_to = period.get('date_to')

                customer_invoice_sale, customer_retail_sale, customer_product_count = self.get_sale_amount_of_pos(
                    period_date_from, period_date_to, salesperson_ids, order_id=order.id)
                customer_discount = customer_retail_sale and (
                        customer_retail_sale - customer_invoice_sale) / customer_retail_sale or 0
                if (customer_invoice_sale != 0 or customer_product_count != 0) and customer_invoice_sale <= 499:
                    update_dict('0-499', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 500 and customer_invoice_sale <= 999:
                    update_dict('500-999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 1000 and customer_invoice_sale <= 1499:
                    update_dict('1,000-1,499', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 1500 and customer_invoice_sale <= 1999:
                    update_dict('1,500-1,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 2000 and customer_invoice_sale <= 2499:
                    update_dict('2,000-2,499', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 2500 and customer_invoice_sale <= 4999:
                    update_dict('2,500-4,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 5000 and customer_invoice_sale <= 7499:
                    update_dict('5,000-7,499', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 7500 and customer_invoice_sale <= 9999:
                    update_dict('7,500-9,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 10000 and customer_invoice_sale <= 14999:
                    update_dict('10,000-14,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 15000 and customer_invoice_sale <= 19999:
                    update_dict('15,000-19,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 20000 and customer_invoice_sale <= 24999:
                    update_dict('20,000-24,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 25000 and customer_invoice_sale <= 29999:
                    update_dict('25,000-29,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 30000 and customer_invoice_sale <= 34999:
                    update_dict('30,000-34,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 35000 and customer_invoice_sale <= 39999:
                    update_dict('35,000-39,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 40000 and customer_invoice_sale <= 44999:
                    update_dict('40,000-44,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 45000 and customer_invoice_sale <= 49999:
                    update_dict('45,000-49,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 50000 and customer_invoice_sale <= 74999:
                    update_dict('50,000-74,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 75000 and customer_invoice_sale <= 99999:
                    update_dict('75,000-99,999', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)
                elif customer_invoice_sale >= 100000:
                    update_dict('100,000+', order.id, period_date_from, [customer_invoice_sale, 'pos'],
                                customer_retail_sale, customer_product_count)

        sale_perc_sum = 0
        sale_perc_sums = 0
        invoice_sale_sum = {}
        product_count_sum = {}
        retail_sale_sum = {}
        current_period_order_ids = {}
        current_price_range_invoice_sale = 0
        # initialize dictionary variable with zero based on periods
        for period in periods:
            invoice_sale_sum[period.get('date_from')] = 0
            product_count_sum[period.get('date_from')] = 0
            retail_sale_sum[period.get('date_from')] = 0

        # iterate with vendor ids
        for key, values in sale_order_price_range_dict.items():
            current_period_order_ids = values
            column = []
            for period in periods:
                period_date_from = period.get('date_from')
                period_date_to = period.get('date_to')

                range_wise_invoice_total = range_wise_invoice_total_dict[key][period_date_from]
                range_retail_sale = range_wise_discount_dict[key][period_date_from]
                customer_discount = range_retail_sale and (
                        range_retail_sale - range_wise_invoice_total) / range_retail_sale or 0
                range_wise_item_count = range_wise_item_count_dict[key][period_date_from]
                invoice_sale_sum[period_date_from] += range_wise_invoice_total
                product_count_sum[period_date_from] += range_wise_item_count
                retail_sale_sum[period_date_from] += range_retail_sale

                if period_date_from == date_from:
                    range_perc = total_invoice_sale and range_wise_invoice_total / total_invoice_sale or 0
                    range_sale_perc = str(self.format_value(round(range_perc * 100, 2))) + '%'
                    sale_perc_sum += range_perc
                    current_price_range_invoice_sale = range_wise_invoice_total

                    range_wise_invoice_total = self.format_value(range_wise_invoice_total)
                    range_wise_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                    column += [{'name': range_wise_invoice_total}, {'name': range_sale_perc},
                               {'name': range_wise_item_count},
                               {'name': range_wise_discount_perc},{'name': ''}, {'name': ''}, {'name': ''}]
                else:
                    range_perc = total_invoice_sale and range_wise_invoice_total / total_invoice_sale or 0
                    range_sale_perc = str(self.format_value(round(range_perc * 100, 2))) + '%'
                    sale_perc_sums += range_perc
                    range_wise_invoice_total = self.format_value(range_wise_invoice_total)
                    current_price_range_invoice_sale = range_wise_invoice_total
                    range_wise_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                    column += [{'name': range_wise_invoice_total}, {'name': range_sale_perc},
                               {'name': range_wise_item_count},
                               {'name': range_wise_discount_perc},{'name': ''}, {'name': ''}, {'name': ''}]

            address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
            lines.append({
                'id': line_id,
                'name': key,
                'unfoldable': False,
                'columns': column,
                'level': 1,
            })

            line_id += 1
            order_ids = []
            if current_period_order_ids:
                sorted_partners_tuple = sorted(current_period_order_ids.items(), key=itemgetter(1), reverse=True)
                order_ids = [[x[0], x[1][1]] for x in sorted_partners_tuple]

            for order_lst in order_ids:
                if order_lst[1] == 'sale':
                    order = self.env['sale.order'].browse(order_lst[0])
                else:
                    order = self.env['pos.order'].browse(order_lst[0])
                customer = order.partner_id
                column = []
                for period in periods:
                    period_date_from = period.get('date_from')
                    period_date_to = period.get('date_to')
                    # called function to get customer wise sales details
                    if order_lst[1] == 'sale':
                        customer_invoice_sale, customer_retail_sale, customer_product_count = self.get_sale_amount(
                            period_date_from, period_date_to, salesperson_ids, customer_id=customer.id,
                            order_id=order.id)
                    else:
                        customer_invoice_sale, customer_retail_sale, customer_product_count = self.get_sale_amount_of_pos(
                            period_date_from, period_date_to, salesperson_ids, customer_id=customer.id,
                            order_id=order.id)
                    customer_discount = customer_retail_sale and (
                            customer_retail_sale - customer_invoice_sale) / customer_retail_sale or 0

                    if period_date_from == date_from:
                        current_price_range_invoice_sale = str(current_price_range_invoice_sale)
                        current_price_range_invoice_sale = current_price_range_invoice_sale.replace(',', '')
                        current_price_range_invoice_sale = float(current_price_range_invoice_sale)
                        customer_perc = current_price_range_invoice_sale and customer_invoice_sale / current_price_range_invoice_sale or 0
                        customer_sale_perc = str(round(customer_perc * 100, 2)) + '%'
                        contact_address, contact_address1, = self._get_address_details(customer)
                        customer_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                        customer_invoice_sale = self.format_value(customer_invoice_sale)
                        column += [{'name': customer_invoice_sale}, {'name': customer_sale_perc},
                                   {'name': customer_product_count},
                                   {'name': customer_discount_perc},{'name':contact_address},{'name':contact_address1},
                                   {'name': order.user_id and order.user_id.name or ''}
                                   ]
                    else:
                        customer_discount_perc = str(self.format_value(round(customer_discount * 100, 2))) + '%'
                        customer_invoice_sale = self.format_value(customer_invoice_sale)
                        customer_invoice_sale = customer_invoice_sale.replace(',','')
                        customer_invoice_sale = float(customer_invoice_sale)
                        customer_perc = current_price_range_invoice_sale and customer_invoice_sale / current_price_range_invoice_sale or 0
                        customer_sale_perc = str(round(customer_perc * 100, 2)) + '%'
                        contact_address, contact_address1, = self._get_address_details(customer)
                        column += [{'name': customer_invoice_sale}, {'name': customer_sale_perc},
                                   {'name': customer_product_count},
                                   {'name': customer_discount_perc},{'name':contact_address},{'name':contact_address1},
                                   {'name': order.user_id and order.user_id.name or ''}]

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
                # if customer.email:
                #     contact_address1 += ' , ' + self.split_multi_emails(customer.email, ';')

                # address_column = [{'name': contact_address}, {'name': contact_address1},
                #                   {'name': order.user_id and order.user_id.name or ''}]

                lines.append({
                    'id': line_id,
                    'name': customer.name,
                    'type': 'line',
                    'unfoldable': False,
                    'columns': column ,
                    'level': 3,
                })
                line_id += 1
        # Total Row
        sale_perc_sum_perc = str(self.format_value(round(sale_perc_sum * 100, 2))) + '%'
        bottom_column = []
        periods = self.remove_duplicated_period(periods)
        # iterate with periods
        for period in periods:
            period_date_from = period.get('date_from')
            period_date_to = period.get('date_to')

            discount = retail_sale_sum[period_date_from] and (
                    retail_sale_sum[period_date_from] - invoice_sale_sum[period_date_from]) / retail_sale_sum[
                           period_date_from] or 0
            discount_sum_perc = str(self.format_value(round(discount * 100, 2))) + '%'
            if period_date_from == date_from:
                bottom_column += [{'name': self.format_value(invoice_sale_sum[period_date_from])},
                                  {'name': sale_perc_sum_perc},
                                  {'name': product_count_sum[period_date_from]}, {'name': discount_sum_perc},{'name': ''}, {'name': ''}, {'name': ''}]
            else:
                sales_perc_sum_perc = str(self.format_value(round(sale_perc_sums * 100, 2))) + '%'
                bottom_column += [{'name': self.format_value(invoice_sale_sum[period_date_from])},
                                  {'name': sales_perc_sum_perc},
                                  {'name': product_count_sum[period_date_from]}, {'name': discount_sum_perc},
                                  {'name': ''}, {'name': ''}, {'name': ''}]
        address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
        lines.append({
            'id': line_id,
            'name': 'Total',
            'unfoldable': False,
            'columns': bottom_column,
            'level': 1,
        })
        line_id += 1
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
