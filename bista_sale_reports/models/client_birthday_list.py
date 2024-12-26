# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from datetime import datetime, timedelta
from operator import itemgetter

import pytz
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo import models, fields, _

MONTH_SELECTION = [
    ('all', 'All Months'),
    ('January', 'January'),
    ('February', 'February'),
    ('March', 'March'),
    ('April', 'April'),
    ('May', 'May'),
    ('June', 'June'),
    ('July', 'July'),
    ('August', 'August'),
    ('September', 'September'),
    ('October', 'October'),
    ('November', 'November'),
    ('December', 'December'),
]


class ClientBirthdayListCustomHandler(models.AbstractModel):
    _name = 'client.birthday.list.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Client Birthday List Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        # current_month = datetime.now().strftime('%B')
        if 'months' not in previous_options:
            options['months'] = [
                {'id': 'All', 'name': _('All Months'), 'selected': False},
                {'id': 'January', 'name': _('January'), 'selected': False},
                {'id': 'February', 'name': _('February'), 'selected': False},
                {'id': 'March', 'name': _('March'), 'selected': False},
                {'id': 'April', 'name': _('April'), 'selected': False},
                {'id': 'May', 'name': _('May'), 'selected': False},
                {'id': 'June', 'name': _('June'), 'selected': False},
                {'id': 'July', 'name': _('July'), 'selected': False},
                {'id': 'August', 'name': _('August'), 'selected': False},
                {'id': 'September', 'name': _('September'), 'selected': False},
                {'id': 'October', 'name': _('October'), 'selected': False},
                {'id': 'November', 'name': _('November'), 'selected': False},
                {'id': 'December', 'name': _('December'), 'selected': False},
            ]
        else:
            options['months'] = previous_options['months']

        # for month in options['months']:
        #     if month['id'] == current_month:
        #         month['selected'] = True

    def _get_customers(self):
        customer_ids = []
        for customer in self.env['res.partner'].search([('customer_rank', '>', 0)]):
            if customer.anniversary_month or customer.birthday_month:
                customer_ids.append(customer.id)
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
    def get_sale_amount(self, date_from, date_to, salesperson_ids, key='birthday', selected_month=[], customer_id=None,
                        get_orders=None, options=None):
        context = self.env.context
        # get salesperson from context

        if date_from:
            date_from = str(date_from) + ' 00:00:00'
        if date_to:
            date_to = str(date_to) +' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        sql = ("""
        select 
            SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) as net_qty
            ,so.user_id as sales_person 
            ,so.id as sales
            ,so.partner_id as partner
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
        from sale_order_line sol
            inner join sale_order so on (so.id = sol.order_id)
            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join product_product pp on (sol.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join res_partner rp on (rp.id = so.partner_id)
            inner join res_users ru on (ru.id = so.user_id)
        where sp.date_done >= '%s' and sp.date_done <= '%s' and ru.id in %s
            and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = sol.product_id 
        """) % (date_from, date_to, salesperson_ids)

        # if month is given, add month filter with the domain
        # if selected_month:
        #     if len(selected_month) == 1:
        #         selected_month_str = "('" + selected_month[0] + "')"
        #     else:
        #         selected_month_str = '(' + ','.join("'" + str(x) + "'" for x in selected_month) + ')'
        #
        #     if key == 'birthday':
        #         sql += " and rp.birthday_month in %s" % selected_month_str
        #     else:
        #         sql += " and rp.anniversary_month in %s" % selected_month_str



        # if selected_month:
        #     selected_month_str = ','.join("'" + str(x) + "'" for x in selected_month)
        #     selected_month = '(' + str(selected_month_str) + ')'
        #     if key == 'birthday':
        #         sql += (""" and rp.birthday_month in %s""") % (selected_month)
        #     else:
        #         sql += (""" and rp.anniversary_month in %s""") % (selected_month)

        # if customer id is given, add customer filter with domain
        # if customer_id:
        #     customer_ids = tuple(customer_id)
        #     customer_ids = self.env['res.partner'].browse(customer_ids)
        #     print(">>>>>", customer_ids)
        #     sql += " and rp.id in %s" % str(tuple(customer_ids.ids))
        # sql += ' group by so.user_id, so.id '

        # if customer_id:
        #     if isinstance(customer_id, int):
        #         customer_ids = (customer_id,)
        #     else:
        #         customer_ids = tuple(customer_id)
        #
        #     customer_records = self.env['res.partner'].browse(customer_ids)
        #     print(">>>>>", customer_records)
        #     sql += " and rp.id in %s" % str(tuple(customer_records.ids))
        #
        # sql += ' group by so.user_id, so.id '

        # if customer_id:
        #     print(">>>>>",customer_id)
        #     sql += (""" and rp.id in %s""")% (customer_id.ids)
        # sql += ' group by so.user_id, so.id '

        if selected_month:
            if len(selected_month) == 1:
                selected_month_str = "'" + selected_month[0] + "'"
            else:
                selected_month_str = ','.join("'" + str(x) + "'" for x in selected_month)

            if key == 'birthday':
                sql += " and rp.birthday_month in (%s)" % selected_month_str
            else:
                sql += " and rp.anniversary_month in (%s)" % selected_month_str

        if customer_id:
            if isinstance(customer_id, int):
                customer_ids = (customer_id,)
            else:
                customer_ids = tuple(customer_id)

            customer_records = self.env['res.partner'].browse(customer_ids)
            print("::::::::::::::", customer_records)
            print(">>>>>", customer_records)

            if len(customer_records) == 1:
                sql += " and rp.id = %s" % customer_records.ids[0]
            elif customer_records:
                sql += " and rp.id in %s" % str(tuple(customer_records.ids))
            else:
                sql += " and 1=0"

        sql += ' group by so.user_id, so.id '

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        partner_ids = []
        invoice_sale = 0
        sales_person = []
        for value in result:
            partner_ids.append(value.get('partner', 0) or 0)
            invoice_sale += value.get('invoice_price', 0) or 0
            sales_person.append(value.get('sales_person', 0) or 0)
        if get_orders:
            return [invoice_sale, partner_ids, sales_person]
        else:
            return [invoice_sale, partner_ids]

    def prepare_sales_persons(self, salesperson_ids):
        if salesperson_ids:
            salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
            salesperson_ids = '(' + salesperson_ids_str + ')'
        else:
            salesperson_ids = self.env['res.users'].search(
                ['|', ('active', '=', False), ('active', '=', True)]).ids
            salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
            salesperson_ids = '(' + salesperson_ids_str + ')'
        return salesperson_ids

    def revert_sales_persons(self, salesperson_ids):
        salesperson_ids = salesperson_ids.replace("(", "")
        salesperson_ids = salesperson_ids.replace(")", "")
        salesperson_ids = salesperson_ids.split(',')
        salesperson_ids = list(map(int, salesperson_ids))
        return salesperson_ids

    def get_sale_amount_of_pos(self, date_from, date_to, salesperson_ids, key='birthday', selected_month=[],
                               customer_id=None, get_orders=None):

        if date_from:
            date_from = str(date_from) + ' 00:00:00'
        if date_to:
            date_to = str(date_to) + ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        sql = ("""
        select 
            SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                    WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                    ELSE 0
               END) as net_qty, po.user_id as sales_person ,po.id as sales, po.partner_id as partner
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
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join res_users ru on (ru.id = po.user_id)
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and ru.id in %s
            and sp.state = 'done' 
            and spt.code in ('outgoing', 'incoming') 
            and sm.product_id = pol.product_id
        """) % (date_from, date_to, salesperson_ids)

        # if month is given, add month filter with the domain
        if selected_month:
            selected_month_str = ','.join("'" + str(x) + "'" for x in selected_month)
            selected_month = '(' + str(selected_month_str) + ')'
            if key == 'birthday':
                sql += (""" and rp.birthday_month in %s""") % (selected_month)
            else:
                sql += (""" and rp.anniversary_month in %s""") % (selected_month)
        #
        # # if customer id is given, add customer filter with domain
        # if customer_id:
        #     customer_ids = tuple(customer_id)  # Convert list to tuple for SQL query
        #     sql += " and rp.id in %s" % (customer_ids,)
        # sql += ' group by po.user_id, po.id '


        if customer_id:
            if isinstance(customer_id, int):
                customer_ids = (customer_id,)
            else:
                customer_ids = tuple(customer_id)

            customer_records = self.env['res.partner'].browse(customer_ids)
            print("::::::::::::::", customer_records)
            print(">>>>>", customer_records)

            if len(customer_records) == 1:
                sql += " and rp.id = %s" % customer_records.ids[0]
            elif customer_records:
                sql += " and rp.id in %s" % str(tuple(customer_records.ids))
            else:
                sql += " and 1=0"

        sql += ' group by po.user_id, po.id '

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        partner_ids = []
        invoice_sale = 0
        sales_person = []
        for value in result:
            partner_ids.append(value.get('partner', 0) or 0)
            invoice_sale += value.get('invoice_price', 0) or 0
            sales_person.append(value.get('sales_person', 0) or 0)
        if get_orders:
            return [invoice_sale, partner_ids, sales_person]
        else:
            return [invoice_sale, partner_ids]

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
                    email += ', ' + x
        return email

    def sort_customers_based_on_dob(self, customer_ids):
        list_to_be_sorted = []
        for customer in self.env['res.partner'].browse(customer_ids):
            if customer.birthday_day:
                list_to_be_sorted.append({'customer_id': customer.id, 'day': customer.birthday_day})
        sorted_list = sorted(list_to_be_sorted, key=itemgetter('day'))
        sorted_customer_ids = [x['customer_id'] for x in sorted_list]
        return sorted_customer_ids

    def sort_customers_based_on_amount(self, customer_amount_list):
        sorted_list = sorted(customer_amount_list, key=itemgetter('amount'), reverse=True)
        sorted_customer_ids = [x['customer_id'] for x in sorted_list]
        return sorted_customer_ids

    def get_month_no(self, month):
        count = 0
        for list in MONTH_SELECTION:
            if month == list[0]:
                break
            count += 1
        return str(count).zfill(2)

    def generate_month_wise_data(self, line_id, key, date_from, date_to, selected_month_list, salesperson_ids):
        # get salesperson from context
        salesperson_ids = self.prepare_sales_persons(salesperson_ids)
        original_salespersons_ids = self.revert_sales_persons(salesperson_ids)

        # called function to find the total ssale for the period
        result_list = self.get_sale_amount(date_from, date_to, salesperson_ids)
        result_list_pos = self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids)

        total_invoice_sale = result_list[0] + result_list_pos[0]
        sale_perc_sum = 0
        invoice_sale_sum = 0
        current_period_customer_ids = []
        lines = []
        for month in selected_month_list:
            column = []
            # called function to get month wise sum and month wise customer details
            month_invoice_sale = self.get_sale_amount(date_from, date_to, salesperson_ids, key=key, selected_month=[month])[0]
            print(">>>>totalinvoicee",month_invoice_sale)
            month_invoice_sale_pos = self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids, key=key, selected_month=[month])[0]
            month_invoice_sale = month_invoice_sale + month_invoice_sale_pos
            month_customer_ids = []
            if key == 'birthday':
                sql = ("""
                        select
                            rp.id as ids
                        from res_partner as rp
                        where rp.customer_rank > 0
                            and rp.birthday_month = '%s'
                        order by birthday_day
                    """) % (month)
            else:
                sql = ("""
                        select
                            rp.id as ids
                        from res_partner as rp
                        where rp.customer_rank > 0
                            and rp.anniversary_month = '%s'
                        order by anniversary_day
                    """) % (month)

            self._cr.execute(sql)
            res = self._cr.fetchall()
            for id in res:
                month_customer_ids.append(id[0])


            month_perc = total_invoice_sale and month_invoice_sale / total_invoice_sale or 0
            column = [{'name': ''}]
            sale_perc_sum += month_perc
            current_period_customer_ids = month_customer_ids
            print(">>mmmmmmmmmmmm",current_period_customer_ids)

            invoice_sale_sum += month_invoice_sale
            column += [{'name': self.format_value(month_invoice_sale)}]
            address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
            lines.append({
                'id': line_id,
                'name': month,
                'unfoldable': False,
                'columns': column + address_column,
                'level': 2,
            })
            line_id += 1
            for customer in self.env['res.partner'].browse(current_period_customer_ids):
                column = []
                order_ids = []
                customer_invoice_sale = 0
                sql = ("""
                        select
                            distinct rp.id
                        from res_partner rp
                            inner join stock_picking sp on (sp.partner_id = rp.id)
                        where sp.date_done >='%s' and sp.date_done<= '%s' and rp.id = %s
                """) % (date_from, date_to, customer.id)
                self._cr.execute(sql)
                res = self._cr.fetchone()
                if res:
                    # called function to get customer wise sales details
                    list_vals = self.get_sale_amount(date_from, date_to, salesperson_ids, key=key,
                                                     selected_month=[month], customer_id=customer.id, get_orders=True)
                    list_vals_pos = self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids, key=key,
                                                                selected_month=[month], customer_id=customer.id,
                                                                get_orders=True)
                    customer_invoice_sale = list_vals[0] + list_vals_pos[0]
                    order_ids = list_vals[2] + list_vals_pos[2]
                if not order_ids:
                    # salesperson_ids = self.revert_sales_persons(salesperson_ids)
                    # salesperson_ids = context.get('user_ids', [])
                    # if not salesperson_ids:
                    #     salesperson_ids = context.get('selected_users_ids', [])

                    if customer.user_id and customer.user_id.id not in original_salespersons_ids:
                        continue
                if key == 'birthday':
                    current_yr_birthday = ''
                    if customer.birthday_month and customer.birthday_day:
                        current_yr_birthday = str(self.get_month_no(customer.birthday_month)) + '-' + str(
                            customer.birthday_day).zfill(2)
                    elif customer.birthday_month:
                        current_yr_birthday = str(self.get_month_no(customer.birthday_month)) + '-00'

                    column = [{'name': current_yr_birthday}]
                elif key == 'anniversary':
                    current_yr_anniversary = ''
                    if customer.anniversary_month and customer.anniversary_day:
                        current_yr_anniversary = str(self.get_month_no(customer.anniversary_month)) + '-' + str(
                            customer.anniversary_day).zfill(2)

                    column = [{'name': current_yr_anniversary}]

                column += [{'name': self.format_value(customer_invoice_sale)}]

                contact_address = ''
                if customer.street:
                    contact_address += customer.street + ', '
                if customer.city:
                    contact_address += customer.city + ', '
                if customer.state_id:
                    contact_address += customer.state_id.name
                if customer.zip:
                    contact_address += ' ' + customer.zip

                contact_address1 = customer.phone or ''
                if contact_address1 and customer.mobile:
                    contact_address1 += ', ' + customer.mobile
                elif customer.mobile:
                    contact_address1 = customer.mobile
                if contact_address1:
                    contact_address1 += ', '
                if customer.email:
                    contact_address1 += self.split_multi_emails(customer.email, ';')
                sp_names = ''
                sp_ids = []
                salesperson_names_str = ''
                if order_ids:
                    for user in self.env['res.users'].browse(order_ids):
                        if user.name not in sp_ids:
                            sp_ids.append(user.name)
                    salesperson_names_str = ', '.join(str(x) for x in sp_ids)
                if not salesperson_names_str and customer.user_id:
                    salesperson_names_str = customer.user_id.name

                address_column = [{'name': contact_address}, {'name': contact_address1},
                                  {'name': salesperson_names_str} or {'name': ''}]
                lines.append({
                    'id': line_id,
                    'name': customer.name,
                    'unfoldable': False,
                    'columns': column + address_column,
                    'level': 3,
                })
                line_id += 1

        # Total Row
        bottom_column = [{'name': ''}]
        bottom_column += [{'name': self.format_value(invoice_sale_sum)}]
        address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
        lines.append({
            'id': line_id,
            'name': 'Total',
            'unfoldable': False,
            'columns': bottom_column + address_column,
            'level': 1,
        })
        line_id += 1
        return lines, line_id

    def generate_year_wise_data(self, line_id, key, date_from, date_to,selected_month_list, salesperson_ids):
        # get salesperson from context
        print("dsssssss",selected_month_list)
        selected_month_str = ','.join("'" + str(x) + "'" for x in selected_month_list)
        selected_month = '(' + str(selected_month_str) + ')'

        salesperson_ids = self.prepare_sales_persons(salesperson_ids)
        original_salespersons_ids = self.revert_sales_persons(salesperson_ids)

        # called function to find the total ssale for the period
        result_list = self.get_sale_amount(date_from, date_to, salesperson_ids)
        result_list_pos = self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids)

        total_invoice_sale = result_list[0] + result_list_pos[0]
        sale_perc_sum = 0
        invoice_sale_sum = 0
        current_period_customer_ids = []
        lines = []

        column = []
        # called function to get month wise sum and month wise customer details
        month_invoice_sale = \
        self.get_sale_amount(date_from, date_to, salesperson_ids)[0]
        print(">>>>totalinvoicee", month_invoice_sale)
        month_invoice_sale_pos = \
        self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids, key=key )[0]
        month_invoice_sale = month_invoice_sale + month_invoice_sale_pos
        month_customer_ids = []
        if key == 'birthday':
            sql = ("""
               SELECT
                    rp.id as ids
                FROM res_partner as rp
                WHERE rp.customer_rank > 0
                    AND rp.birthday_month IN %s
                    or   (rp.anniversary_month IN %s)
                ORDER BY birthday_day , anniversary_day;
            """)% (selected_month,selected_month)

            self._cr.execute(sql)
            print("sqqqqqqqq",sql)
        res = self._cr.fetchall()

        month_perc = total_invoice_sale and month_invoice_sale / total_invoice_sale or 0
        column = [{'name': ''}]
        sale_perc_sum += month_perc
        current_period_customer_ids = [id[0] for id in res]

        # current_period_customer_ids = ([i[0] for i in res])
        print("curereee",current_period_customer_ids)
        invoice_sale_sum += month_invoice_sale
        column += [{'name': self.format_value(month_invoice_sale)}]
        address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
        lines.append({
            'id': line_id,
            'unfoldable': False,
            'columns': column + address_column,
            'level': 2,
        })
        line_id += 1
        sql = """
            SELECT DISTINCT rp.id
            FROM res_partner rp
            INNER JOIN stock_picking sp ON (sp.partner_id = rp.id)
            WHERE sp.date_done > '%s' AND sp.date_done <= '%s' AND rp.id in %s
        """ % (date_from, date_to, tuple(current_period_customer_ids))

        self._cr.execute(sql)
        res = self._cr.fetchone()
        print(">>sasssssssssss",sql)
        print(">>sasssssssssss",res)


        # for customer in self.env['res.partner'].browse(current_period_customer_ids):
        column = []
        order_ids = []
        customer_invoice_sale = 0
        print("cccccccccccustemer",current_period_customer_ids)
        if res:
            # called function to get customer wise sales details
            list_vals = self.get_sale_amount(date_from, date_to, salesperson_ids, key=key,
                                         customer_id=current_period_customer_ids, get_orders=True)
            list_vals_pos = self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids, key=key,
                                                         customer_id=current_period_customer_ids,
                                                        get_orders=True)
            customer_invoice_sale = list_vals[0] + list_vals_pos[0]
            order_ids = list_vals[2] + list_vals_pos[2]
        if not order_ids:
            # salesperson_ids = self.revert_sales_persons(salesperson_ids)
            # salesperson_ids = context.get('user_ids', [])
            # if not salesperson_ids:
            #     salesperson_ids = context.get('selected_users_ids', [])
            for customer in current_period_customer_ids:
                if customer.user_id and customer.user_id.id not in original_salespersons_ids:
                    continue
        for customer in self.env['res.partner'].browse(current_period_customer_ids):
            print("ssss",customer)
            if key == 'birthday':
                current_yr_birthday = ''
                if customer.birthday_month and customer.birthday_day:
                    current_yr_birthday = str(self.get_month_no(customer.birthday_month)) + '-' + str(
                        customer.birthday_day).zfill(2)
                elif customer.birthday_month:
                    current_yr_birthday = str(self.get_month_no(customer.birthday_month)) + '-00'

                column = [{'name': current_yr_birthday}]
            elif key == 'anniversary':
                current_yr_anniversary = ''
                if customer.anniversary_month and customer.anniversary_day:
                    current_yr_anniversary = str(self.get_month_no(customer.anniversary_month)) + '-' + str(
                        customer.anniversary_day).zfill(2)

                column = [{'name': current_yr_anniversary}]

            column += [{'name': self.format_value(customer_invoice_sale)}]

            contact_address = ''
            if customer.street:
                contact_address += customer.street + ', '
            if customer.city:
                contact_address += customer.city + ', '
            if customer.state_id:
                contact_address += customer.state_id.name
            if customer.zip:
                contact_address += ' ' + customer.zip

            contact_address1 = customer.phone or ''
            if contact_address1 and customer.mobile:
                contact_address1 += ', ' + customer.mobile
            elif customer.mobile:
                contact_address1 = customer.mobile
            if contact_address1:
                contact_address1 += ', '
            if customer.email:
                contact_address1 += self.split_multi_emails(customer.email, ';')
            sp_names = ''
            sp_ids = []
            salesperson_names_str = ''
            if order_ids:
                for user in self.env['res.users'].browse(order_ids):
                    if user.name not in sp_ids:
                        sp_ids.append(user.name)
                salesperson_names_str = ', '.join(str(x) for x in sp_ids)
            if not salesperson_names_str and customer.user_id:
                salesperson_names_str = customer.user_id.name

            address_column = [{'name': contact_address}, {'name': contact_address1},
                              {'name': salesperson_names_str} or {'name': ''}]
            lines.append({
                'id': line_id,
                'name': customer.name,
                'unfoldable': False,
                'columns': column + address_column,
                'level': 3,
            })
            line_id += 1

        # Total Row
        bottom_column = [{'name': ''}]
        bottom_column += [{'name': self.format_value(invoice_sale_sum)}]
        address_column = [{'name': ''}, {'name': ''}, {'name': ''}]
        lines.append({
            'id': line_id,
            'name': 'Total',
            'unfoldable': False,
            'columns': bottom_column + address_column,
            'level': 1,
        })
        line_id += 1
        return lines, line_id

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format.encode('UTF-8')
        lines = []
        context = self.env.context
        line_id = 0

        lines.append({
            'id': line_id,
            'name': '',
            'unfoldable': False,
            'columns': [
                {'name': _('MM-DD')},
                {'name': _('YTD'), 'class': 'number'},
                {'name': _('Street, City, State Zip')},
                {'name': _('Phone, Mobile, Email')},
                {'name': _('SP'), 'class': 'number'}],
            'level': 1,
        })
        line_id += 1
        company_id = context.get('company_id') or self.env.user.company_id
        date_to = context.get('date_to', False)
        if not date_to:
            if options.get('date'):
                date_to = options['date'].get('date_to') or options['date'].get('date')

        date_to_obj = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT).date()
        fiscalyear_last_day = company_id.fiscalyear_last_day
        fiscalyear_last_month = company_id.fiscalyear_last_month

        # fiscalyear_last_date = date_to_obj.replace(month=fiscalyear_last_month, day=fiscalyear_last_day)
        fiscalyear_last_date = date_to_obj.replace(month=int(fiscalyear_last_month), day=int(fiscalyear_last_day))

        if fiscalyear_last_date < date_to_obj:
            date_from = str(fiscalyear_last_date + timedelta(days=1))
        else:
            date_from = str(fiscalyear_last_date + timedelta(days=1) - relativedelta(years=+1))

        selected_month = []
        for month in options.get('months'):
            if month.get('selected'):
                selected_month.append(month.get('name'))

        if 'All Months' in selected_month:
            selected_month_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                   'September', 'October', 'November', 'December']
        else:
            selected_month_list = selected_month

        salesperson_ids = options.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = options.get('selected_users_ids', [])
        if salesperson_ids:
            salesperson_ids = salesperson_ids
        # if salesperson_ids:
        if len(selected_month_list) == 12:
            print("alllll",selected_month_list)
            current_year = datetime.now().year
            date_from = datetime(current_year, 1, 1).date()
            date_to = datetime(current_year, 12, 31).date()
            formatted_date_from = date_from.strftime("%Y-%m-%d")
            formatted_date_to = date_to.strftime("%Y-%m-%d")
            row_lines, line_id = self.generate_year_wise_data(line_id, 'birthday', formatted_date_from, formatted_date_to,
                                                               selected_month_list,salesperson_ids)
        else:
            row_lines, line_id = self.generate_month_wise_data(line_id, 'birthday', date_from, date_to,
                                                           selected_month_list, salesperson_ids)
        lines += row_lines
        lines.append({
            'id': line_id,
            'name': '',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 5)],
            'level': 2,
        })
        line_id += 1

        lines.append({
            'id': line_id,
            'name': 'Anniversary',
            'type': 'line_solid',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 5)],
            'level': 0,
        })
        line_id += 1

        lines.append({
            'id': line_id,
            'name': '',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 5)],
            'level': 1,
        })
        line_id += 1

        lines.append({
            'id': line_id,
            'name': '',
            'unfoldable': False,
            'columns': [
                {'name': _('MM-DD')},
                {'name': _('YTD'), 'class': 'number'},
                {'name': _('Street, City, State Zip')},
                {'name': _('Phone, Mobile, Email')},
                {'name': _('SP'), 'class': 'number'},
            ],
            'level': 1,
        })
        line_id += 1
        if len(selected_month_list) == 12 and salesperson_ids:
            print("alllll")
            current_year = datetime.now().year
            date_from = datetime(current_year, 1, 1).date()
            date_to = datetime(current_year, 12, 31).date()
            formatted_date_from = date_from.strftime("%Y-%m-%d")
            formatted_date_to = date_to.strftime("%Y-%m-%d")
            print(">>>Saaaaaaa",salesperson_ids)
            row_lines, line_id = self.generate_year_wise_data(line_id, 'birthday', formatted_date_from, formatted_date_to,
                                                               salesperson_ids)
        else:
            row_lines, line_id = self.generate_month_wise_data(line_id, 'anniversary', date_from, date_to,
                                                           selected_month_list, salesperson_ids)
        lines += row_lines
        return [(0, line) for line in lines]
