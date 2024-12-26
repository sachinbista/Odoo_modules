# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from datetime import datetime, timedelta
from operator import add

import pytz
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from six import string_types

from odoo import models, fields, _


class SalesPerformanceReportCustomHandler(models.AbstractModel):
    _name = 'sales.performance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Sales Performance Report Custom Handler'

    def get_date_with_tz(self, date):
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        datetime_with_tz = fields.Datetime.from_string(date).astimezone(timezone).date() 
        date = datetime_with_tz.strftime('%Y-%m-%d %H:%M:%S')
        return date

    def get_planned_values(self, goal_for, start_date, end_date, salesperson_ids, get_count=None):
        domain = [('user_id', 'in', salesperson_ids), ('start_date', '<=', end_date),
                  ('end_date', '>=', start_date),
                  ('goal_for', '=', goal_for), ]
        goals = self.env['gamification.goal'].search(domain)
        target_goal = 0.00
        if get_count:
            count = 0
        for goal in goals:
            target_goal += goal.target_goal
            if get_count:
                count += 1
        if get_count:
            return target_goal, count
        return target_goal

    def get_sale_amount(self, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date,llyr_date_from,llyr_date_to, salesperson_ids, sale_type='sale', check_delivery=None):
        context = self.env.context
        # user_ids = self.env['res.users'].browse(salesperson_ids)
        salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
        salesperson_ids = '(' + salesperson_ids_str + ')'
        user_ids = context.get('user_ids', [])
        retail_sale = 0.00
        invoice_sale = 0.00
        gross_margin = 0.00
        ly_mnth_retail_amount =0.00
        ly_mnth_invoice_amount= 0.00
        ly_mnth_gross_amount = 0.00
        yr_retail_amount = 0.00
        yr_invoice_amount = 0.00
        yr_gross_amount = 0.00 
        ly_yr_retail_amount = 0.00 
        ly_yr_invoice_amount = 0.00
        ly_yr_gross_amount = 0.00
        ly_yr_retail_amount = 0.00 
        ly_yr_invoice_amount = 0.00
        ly_yr_gross_amount = 0.00
        lly_yr_retail_amount = 0.00
        lly_yr_invoice_amount = 0.00
        lly_yr_gross_amount = 0.00
        other_retail_sale = 0.00
        other_invoice_sale = 0.00
        other_gross_margin = 0.00
        other_ly_mnth_retail_amount = 0.00
        other_ly_mnth_invoice_amount = 0.00
        other_ly_mnth_gross_amount = 0.00
        other_yr_retail_amount = 0.00
        other_yr_invoice_amount = 0.00
        other_yr_gross_amount = 0.00
        other_ly_yr_retail_amount = 0.00
        other_ly_yr_invoice_amount = 0.00
        other_ly_yr_gross_amount = 0.00
        other_lly_yr_retail_amount = 0.00
        other_lly_yr_invoice_amount = 0.00
        other_lly_yr_gross_amount = 0.00
        if sale_type in ['service', 'repair']:
            if user_ids:
                for user_id in user_ids:
                    sql = ("""
                        select 
                        sum(sol.product_uom_qty)
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as sale_price
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as invoice_price 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        ,0.0  as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report != True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                         select 
                        sum(sol.product_uom_qty)
                        , 0.0 as  sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as ly_mnth_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as ly_mnth_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        ,0.0  as lly_yr_gross_amount

                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report != True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                         select 
                        sum(sol.product_uom_qty)
                        , 0.0 as  sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as yr_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as yr_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        ,0.0  as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report != True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                         select 
                        sum(sol.product_uom_qty)
                        , 0.0 as  sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as ly_yr_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as ly_yr_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        ,0.0  as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report != True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                         select 
                        sum(sol.product_uom_qty)
                        , 0.0 as  sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as lly_yr_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as lly_yr_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report != True 
                        group by so.id, pt.id, sol.id, pp.id
                    """) % (date_from, date_to, user_id.id,last_yr_month_start_date,last_yr_date_to,user_id.id,fiscalyear_start_date,date_to,user_id.id,last_yr_fiscalyear_start_date,last_yr_date_to,user_id.id,llyr_date_from,llyr_date_to,user_id.id)


                    self._cr.execute(sql)
                    result = self._cr.dictfetchall()

                    for value in result:
                        retail_sale += value.get('sale_price', 0.00) or 0.00
                        invoice_sale += value.get('invoice_price', 0.00) or 0.00
                        gross_margin += value.get('gross_margin', 0.00) or 0.00
                        ly_mnth_retail_amount += value.get('ly_mnth_retail_amount', 0.00) or 0.00
                        ly_mnth_invoice_amount += value.get('ly_mnth_invoice_amount', 0.00) or 0.00
                        ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0.00) or 0.00
                        yr_retail_amount += value.get('yr_retail_amount', 0.00) or 0.00
                        yr_invoice_amount += value.get('yr_invoice_amount', 0.00) or 0.00
                        yr_gross_amount += value.get('yr_gross_amount', 0.00) or 0.00
                        ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0.00) or 0.00
                        ly_yr_invoice_amount += value.get('ly_yr_invoice_amount', 0.00) or 0.00
                        ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0.00) or 0.00
                        lly_yr_retail_amount+= value.get('lly_yr_retail_amount', 0.00) or 0.00 
                        lly_yr_invoice_amount+= value.get('lly_yr_invoice_amount', 0.00) or 0.00 
                        lly_yr_gross_amount+= value.get('lly_yr_gross_amount', 0.00) or 0.00 

                    other_sql = ("""
                            select 
                            sum(sol.product_uom_qty)
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as sale_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) - (((((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)) end) as invoice_price 
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else ((sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) / so.user_count end) as gross_margin        
                            , 0.0 as other_ly_mnth_retail_amount
                            , 0.0 as other_ly_mnth_invoice_amount
                            , 0.0 as other_ly_mnth_gross_amount
                            , 0.0 as other_yr_retail_amount
                            ,0.0 as other_yr_invoice_amount
                            ,0.0 as other_yr_gross_amount
                            ,0.0 as other_ly_yr_retail_amount
                            ,0.0 as other_ly_yr_invoice_amount
                            ,0.0 as other_ly_yr_gross_amount
                            , 0.0 as other_lly_yr_retail_amount
                            , 0.0 as other_lly_yr_invoice_amount
                            ,0.0  as other_lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id) 
                            inner join product_category pc on (pc.id = pt.categ_id)
                            inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and other.res_users_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                        select 
                            sum(sol.product_uom_qty)
                            , 0.0 as  sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_ly_mnth_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) - (((((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)) end) as other_ly_mnth_invoice_amount 
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else ((sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) / so.user_count end) as other_ly_mnth_gross_amount        
                            , 0.0 as other_yr_retail_amount
                            ,0.0 as other_yr_invoice_amount
                            ,0.0 as other_yr_gross_amount
                            ,0.0 as other_ly_yr_retail_amount
                            ,0.0 as other_ly_yr_invoice_amount
                            ,0.0 as other_ly_yr_gross_amount
                            , 0.0 as other_lly_yr_retail_amount
                            , 0.0 as other_lly_yr_invoice_amount
                            ,0.0  as other_lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id) 
                            inner join product_category pc on (pc.id = pt.categ_id)
                            inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and other.res_users_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                        select 
                            sum(sol.product_uom_qty)
                            , 0.0 as  sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            , 0.0 as other_ly_mnth_retail_amount
                            , 0.0 as other_ly_mnth_invoice_amount
                            , 0.0 as other_ly_mnth_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) - (((((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)) end) as other_yr_invoice_amount 
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else ((sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) / so.user_count end) as other_yr_gross_amount        
                            ,0.0 as other_ly_yr_retail_amount
                            ,0.0 as other_ly_yr_invoice_amount
                            ,0.0 as other_ly_yr_gross_amount
                            , 0.0 as other_lly_yr_retail_amount
                            , 0.0 as other_lly_yr_invoice_amount
                            ,0.0  as other_lly_yr_gross_amount

                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id) 
                            inner join product_category pc on (pc.id = pt.categ_id)
                            inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and other.res_users_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                        select 
                            sum(sol.product_uom_qty)
                            , 0.0 as  sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            , 0.0 as other_ly_mnth_retail_amount
                            , 0.0 as other_ly_mnth_invoice_amount
                            , 0.0 as other_ly_mnth_gross_amount
                            , 0.0 as other_yr_retail_amount
                            ,0.0 as other_yr_invoice_amount
                            ,0.0 as other_yr_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_ly_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) - (((((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)) end) as other_ly_yr_invoice_amount 
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else ((sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) / so.user_count end) as other_ly_yr_gross_amount        
                            , 0.0 as other_lly_yr_retail_amount
                            , 0.0 as other_lly_yr_invoice_amount
                            ,0.0  as other_lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id) 
                            inner join product_category pc on (pc.id = pt.categ_id)
                            inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and other.res_users_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id, pt.id, sol.id, pp.id
                        UNION
                        select 
                            sum(sol.product_uom_qty)
                            , 0.0 as  sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            , 0.0 as other_ly_mnth_retail_amount
                            , 0.0 as other_ly_mnth_invoice_amount
                            , 0.0 as other_ly_mnth_gross_amount
                            , 0.0 as other_yr_retail_amount
                            ,0.0 as other_yr_invoice_amount
                            ,0.0 as other_yr_gross_amount
                            ,0.0 as other_ly_yr_retail_amount
                            ,0.0 as other_ly_yr_invoice_amount
                            ,0.0 as other_ly_yr_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_lly_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) - (((((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)) end) as other_lly_yr_invoice_amount 
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else ((sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count)end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) / so.user_count end) as other_lly_yr_gross_amount        
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id) 
                            inner join product_category pc on (pc.id = pt.categ_id)
                            inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and other.res_users_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id, pt.id, sol.id, pp.id

                    """) % (date_from, date_to, user_id.id,last_yr_month_start_date,last_yr_date_to,user_id.id,fiscalyear_start_date,date_to,user_id.id,last_yr_fiscalyear_start_date,last_yr_date_to,user_id.id,llyr_date_from,llyr_date_to,user_id.id)
                    self._cr.execute(other_sql)
                    other_result = self._cr.dictfetchall()
                    for other_value in other_result:
                        other_retail_sale += other_value.get('sale_price', 0.00) or 0.00
                        other_invoice_sale += other_value.get('invoice_price', 0.00) or 0.00
                        other_gross_margin += other_value.get('gross_margin', 0.00) or 0.00
                        other_ly_mnth_retail_amount+= other_value.get('other_ly_mnth_retail_amount', 0.00) or 0.00
                        other_ly_mnth_invoice_amount += other_value.get('other_ly_mnth_invoice_amount', 0.00) or 0.00
                        other_ly_mnth_gross_amount += other_value.get('other_ly_mnth_gross_amount', 0.00) or 0.00
                        other_yr_retail_amount += other_value.get('other_yr_retail_amount', 0.00) or 0.00
                        other_yr_invoice_amount += other_value.get('other_yr_invoice_amount', 0.00) or 0.00
                        other_yr_gross_amount += other_value.get('other_yr_gross_amount', 0.00) or 0.00
                        other_ly_yr_retail_amount += other_value.get('other_ly_yr_retail_amount', 0.00) or 0.00
                        other_ly_yr_invoice_amount += other_value.get('other_ly_yr_invoice_amount', 0.00) or 0.00
                        other_ly_yr_gross_amount += other_value.get('other_ly_yr_gross_amount', 0.00) or 0.00
                        other_lly_yr_retail_amount+= other_value.get('other_lly_yr_retail_amount', 0.00) or 0.00
                        other_lly_yr_invoice_amount+= other_value.get('other_lly_yr_invoice_amount', 0.00) or 0.00
                        other_lly_yr_gross_amount+= other_value.get('other_lly_yr_gross_amount', 0.00) or 0.00
            else:
                sql = ("""
                    select 
                        sum(sol.product_uom_qty)
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as sale_price
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as invoice_price 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        , 0.0 as lly_yr_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        inner join account_move ai on (ai.id = ail.move_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where ai.payment_state in ('paid','in_payment') 
                        and ai.invoice_date >= '%s' 
                        and ai.invoice_date <= '%s' 
                        and pt.exclude_from_report !=True 
                    group by so.id, pt.id, sol.id, pp.id
                    UNION
                    select 
                        sum(sol.product_uom_qty)
                        ,0.0 as sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as ly_mnth_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as ly_mnth_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        , 0.0 as lly_yr_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        inner join account_move ai on (ai.id = ail.move_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where ai.payment_state in ('paid','in_payment') 
                        and ai.invoice_date >= '%s' 
                        and ai.invoice_date <= '%s' 
                        and pt.exclude_from_report !=True 
                    group by so.id, pt.id, sol.id, pp.id
                    UNION 
                    select 
                        sum(sol.product_uom_qty)
                        ,0.0 as sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as yr_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as yr_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        , 0.0 as lly_yr_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        inner join account_move ai on (ai.id = ail.move_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where ai.payment_state in ('paid','in_payment') 
                        and ai.invoice_date >= '%s' 
                        and ai.invoice_date <= '%s' 
                        and pt.exclude_from_report !=True 
                    group by so.id, pt.id, sol.id, pp.id
                    UNION 
                    select 
                        sum(sol.product_uom_qty)
                        ,0.0 as sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as ly_yr_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as ly_yr_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_yr_gross_amount
                        , 0.0 as lly_yr_retail_amount
                        , 0.0 as lly_yr_invoice_amount
                        , 0.0 as lly_yr_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        inner join account_move ai on (ai.id = ail.move_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where ai.payment_state in ('paid','in_payment') 
                        and ai.invoice_date >= '%s' 
                        and ai.invoice_date <= '%s' 
                        and pt.exclude_from_report !=True 
                    group by so.id, pt.id, sol.id, pp.id
                    UNION
                    select 
                        sum(sol.product_uom_qty)
                        ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as lly_yr_retail_amount
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - ((((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0)) end) as lly_yr_invoice_amount 
                        ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as lly_yr_gross_amount
                        ,0.0 as sale_price
                        , 0.0 as invoice_price
                        , 0.0 as gross_margin
                        , 0.0 as ly_mnth_retail_amount
                        , 0.0 as ly_mnth_invoice_amount
                        , 0.0 as ly_mnth_gross_amount
                        , 0.0 as yr_retail_amount
                        ,0.0 as yr_invoice_amount
                        ,0.0 as yr_gross_amount
                        ,0.0 as ly_yr_retail_amount
                        ,0.0 as ly_yr_invoice_amount
                        ,0.0 as ly_yr_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        inner join account_move ai on (ai.id = ail.move_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where ai.payment_state in ('paid','in_payment') 
                        and ai.invoice_date >= '%s' 
                        and ai.invoice_date <= '%s' 
                        and pt.exclude_from_report !=True 
                    group by so.id, pt.id, sol.id, pp.id
                    """) %  (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
                self._cr.execute(sql)
                result = self._cr.dictfetchall()
                for value in result:
                    retail_sale += value.get('sale_price', 0.00) or 0.00
                    invoice_sale += value.get('invoice_price', 0.00) or 0.00
                    gross_margin += value.get('gross_margin', 0.00) or 0.00
                    ly_mnth_retail_amount += value.get('ly_mnth_retail_amount', 0.00) or 0.00
                    ly_mnth_invoice_amount += value.get('ly_mnth_invoice_amount', 0.00) or 0.00
                    ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0.00) or 0.00
                    yr_retail_amount += value.get('yr_retail_amount', 0.00) or 0.00
                    yr_invoice_amount += value.get('yr_invoice_amount', 0.00) or 0.00
                    yr_gross_amount += value.get('yr_gross_amount', 0.00) or 0.00
                    ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0.00) or 0.00
                    ly_yr_invoice_amount += value.get('ly_yr_invoice_amount', 0.00) or 0.00
                    ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0.00) or 0.00
                    lly_yr_retail_amount+= value.get('lly_yr_retail_amount', 0.00) or 0.00 
                    lly_yr_invoice_amount+= value.get('lly_yr_invoice_amount', 0.00) or 0.00 
                    lly_yr_gross_amount+= value.get('lly_yr_gross_amount', 0.00) or 0.00 

        else:
            if check_delivery:
                if user_ids:
                    for user_id in user_ids:
                        # Commented to Optimise
                        # sql = ("""
                        #     select
                        #         sum(sm.product_uom_qty)
                        #         ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as sale_price
                        #         ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) -(((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as invoice_price
                        #         ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as gross_margin
                        #     from sale_order_line sol
                        #         inner join sale_order so on (so.id = sol.order_id)
                        #         inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        #         inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        #         inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        #         inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        #         inner join account_move ai on (ai.id = ail.move_id)
                        #         inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        #         inner join res_partner rp on (rp.id = so.partner_id)
                        #         inner join product_product pp on (sol.product_id = pp.id)
                        #         inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        #         inner join product_category pc on (pc.id = pt.categ_id)
                        #     where ai.invoice_date >= '%s'
                        #         and ai.invoice_date <= '%s'
                        #         and sp.state = 'done'
                        #         and spt.code='outgoing'
                        #         and sm.product_id = sol.product_id
                        #         and so.user_id = %s
                        #         and pt.exclude_from_report = False
                        #         and pc.sale_type = '%s'
                        #     group by so.id,pt.id,sol.id,sm.id,pp.id
                        #         """) % (date_from, date_to, user_id.id, sale_type)

                        sql = ("""
                            select
                                sum(sm.product_uom_qty)
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as sale_price
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_sale_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) -(((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as other_invoice_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as invoice_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as gross_margin
                                ,(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty)/so.user_count else (sol.price_unit*sm.product_uom_qty)-(((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0)/so.user_count end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/so.user_count end)  as other_gross_margin
                                , 0.0 as  ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_gross_amount
                                ,0.0 as other_ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                ,0.0 as other_yr_retail_amount
                                ,0.0 as other_yr_invoice_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as  other_yr_gross_amount
                                , 0.0 as ly_yr_retail_amount
                                ,0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as  ly_yr_gross_amount
                                , 0.0 as other_ly_yr_gross_amount
                                ,0.0 as lly_yr_retail_amount
                                ,0.0 as other_lly_yr_retail_amount
                                ,0.0 as other_lly_yr_invoice_amount
                                ,0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                                ,0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id)
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                            where ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s'
                                and sp.state = 'done' 
                                and spt.code='outgoing' 
                                and sm.state='done'
                                and sm.product_id = sol.product_id
                                and other.res_users_id = %s 
                                and so.user_id = %s
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION All
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as other_sale_price
                                ,0.0 as other_invoice_price
                                ,0.0 as invoice_price
                                ,0.0 as gross_margin
                                ,0.0 as other_gross_margin
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as ly_mnth_retail_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_ly_mnth_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) -(((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as other_ly_mnth_invoice_amount 
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as ly_mnth_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_mnth_gross_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty)/so.user_count else (sol.price_unit*sm.product_uom_qty)-(((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0)/so.user_count end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/so.user_count end)  as other_ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                ,0.0 as other_yr_retail_amount
                                ,0.0 as other_yr_invoice_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as  other_yr_gross_amount
                                , 0.0 as ly_yr_retail_amount
                                ,0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as  ly_yr_gross_amount
                                , 0.0 as other_ly_yr_gross_amount
                                ,0.0 as lly_yr_retail_amount
                                ,0.0 as other_lly_yr_retail_amount
                                ,0.0 as other_lly_yr_invoice_amount
                                ,0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                                ,0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id)
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                            where ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s'
                                and sp.state = 'done' 
                                and spt.code='outgoing' 
                                and sm.state='done'
                                and sm.product_id = sol.product_id
                                and other.res_users_id = %s 
                                and so.user_id = %s
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION ALL
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as other_sale_price
                                ,0.0 as other_invoice_price
                                ,0.0 as invoice_price
                                ,0.0 as gross_margin
                                ,0.0 as other_gross_margin
                                , 0.0 as  ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_gross_amount
                                ,0.0 as other_ly_mnth_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as yr_retail_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) -(((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as other_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as yr_gross_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty)/so.user_count else (sol.price_unit*sm.product_uom_qty)-(((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0)/so.user_count end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/so.user_count end)  as other_yr_gross_amount
                                , 0.0 as ly_yr_retail_amount
                                ,0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as  ly_yr_gross_amount
                                , 0.0 as other_ly_yr_gross_amount
                                ,0.0 as lly_yr_retail_amount
                                ,0.0 as other_lly_yr_retail_amount
                                ,0.0 as other_lly_yr_invoice_amount
                                ,0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                                ,0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id)
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                            where ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s'
                                and sp.state = 'done' 
                                and spt.code='outgoing' 
                                and sm.state='done'
                                and sm.product_id = sol.product_id
                                and other.res_users_id = %s 
                                and so.user_id = %s
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION ALL
                            select
                                sum(sm.product_uom_qty)
                                 , 0.0 as sale_price
                                , 0.0 as other_sale_price
                                ,0.0 as other_invoice_price
                                ,0.0 as invoice_price
                                ,0.0 as gross_margin
                                ,0.0 as other_gross_margin
                                , 0.0 as  ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_gross_amount
                                ,0.0 as other_ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                ,0.0 as other_yr_retail_amount
                                ,0.0 as other_yr_invoice_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as  other_yr_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as ly_yr_retail_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_ly_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) -(((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as other_ly_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as ly_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_yr_gross_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty)/so.user_count else (sol.price_unit*sm.product_uom_qty)-(((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0)/so.user_count end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/so.user_count end)  as other_ly_yr_gross_amount
                                ,0.0 as lly_yr_retail_amount
                                ,0.0 as other_lly_yr_retail_amount
                                ,0.0 as other_lly_yr_invoice_amount
                                ,0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                                ,0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id)
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                            where ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s'
                                and sp.state = 'done' 
                                and spt.code='outgoing' 
                                and sm.state='done'
                                and sm.product_id = sol.product_id
                                and other.res_users_id = %s 
                                and so.user_id = %s
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION ALL
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as other_sale_price
                                ,0.0 as other_invoice_price
                                ,0.0 as invoice_price
                                ,0.0 as gross_margin
                                ,0.0 as other_gross_margin
                                , 0.0 as  ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_invoice_amount
                                ,0.0 as ly_mnth_gross_amount
                                ,0.0 as other_ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                ,0.0 as other_yr_retail_amount
                                ,0.0 as other_yr_invoice_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as  other_yr_gross_amount
                                , 0.0 as ly_yr_retail_amount
                                ,0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as  ly_yr_gross_amount
                                , 0.0 as other_ly_yr_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as lly_yr_retail_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as other_lly_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) -(((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as other_lly_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as lly_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as lly_yr_gross_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty)/so.user_count else (sol.price_unit*sm.product_uom_qty)-(((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0)/so.user_count end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/so.user_count end)  as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                                inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id)
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                            where ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s'
                                and sp.state = 'done' 
                                and spt.code='outgoing' 
                                and sm.state='done'
                                and sm.product_id = sol.product_id
                                and other.res_users_id = %s 
                                and so.user_id = %s
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                                """) % (date_from, date_to,user_id.id, user_id.id,last_yr_month_start_date,last_yr_date_to,user_id.id, user_id.id,fiscalyear_start_date,date_to,user_id.id, user_id.id,last_yr_fiscalyear_start_date,last_yr_date_to,user_id.id, user_id.id,llyr_date_from,llyr_date_to,user_id.id,user_id.id)

                        # Commented to Optimise
                        # other_sql = ("""
                        #     select
                        #         sum(sm.product_uom_qty)
                        #         ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) / so.user_count else (sol.price_unit * sol.product_uom_qty) / so.user_count end) as sale_price
                        #         ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as invoice_price
                        #         ,(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty)/so.user_count else (sol.price_unit*sm.product_uom_qty)-(((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0)/so.user_count end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/so.user_count end)  as gross_margin
                        #     from sale_order_line sol
                        #         inner join sale_order so on (so.id = sol.order_id)
                        #         inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        #         inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        #         inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                        #         inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                        #         inner join account_move ai on (ai.id = ail.move_id)
                        #         inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        #         inner join res_partner rp on (rp.id = so.partner_id)
                        #         inner join product_product pp on (sol.product_id = pp.id)
                        #         inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        #         inner join product_category pc on (pc.id = pt.categ_id)
                        #         inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                        #     where ai.invoice_date >= '%s'
                        #         and ai.invoice_date <= '%s'
                        #         and sp.state = 'done'
                        #         and spt.code='outgoing'
                        #         and sm.product_id = sol.product_id
                        #         and other.res_users_id = %s
                        #         and pt.exclude_from_report = False
                        #         and pc.sale_type = '%s'
                        #     group by so.id,pt.id,sol.id,sm.id,pp.id
                        #     """) % (date_from, date_to, user_id.id, sale_type)

                        self._cr.execute(sql)
                        result = self._cr.dictfetchall()
                        for value in result:
                            retail_sale += value.get('sale_price', 0) or 0
                            retail_sale += value.get('other_sale_price', 0) or 0
                            invoice_sale += value.get('invoice_price', 0) or 0
                            invoice_sale += value.get('other_invoice_price', 0) or 0
                            gross_margin += value.get('gross_margin', 0) or 0
                            gross_margin += value.get('other_gross_margin', 0) or 0

                            ly_mnth_retail_amount += value.get('ly_mnth_retail_amount', 0) or 0
                            ly_mnth_retail_amount += value.get('other_ly_mnth_retail_amount', 0) or 0
                            ly_mnth_invoice_amount += value.get('ly_mnth_invoice_amount', 0) or 0
                            ly_mnth_invoice_amount += value.get('other_ly_mnth_invoice_amount', 0) or 0
                            ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0) or 0
                            ly_mnth_gross_amount += value.get('other_ly_mnth_gross_amount', 0) or 0

                            yr_retail_amount += value.get('yr_retail_amount', 0) or 0
                            yr_retail_amount += value.get('other_yr_retail_amount', 0) or 0
                            yr_invoice_amount += value.get('yr_invoice_amount', 0) or 0
                            yr_invoice_amount += value.get('other_yr_invoice_amount', 0) or 0
                            yr_gross_amount += value.get('yr_gross_amount', 0) or 0
                            yr_gross_amount += value.get('other_yr_gross_amount', 0) or 0

                            ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0) or 0
                            ly_yr_retail_amount += value.get('other_ly_yr_retail_amount', 0) or 0
                            ly_yr_invoice_amount += value.get('ly_yr_invoice_amount', 0) or 0
                            ly_yr_invoice_amount += value.get('other_ly_yr_invoice_amount', 0) or 0
                            ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0) or 0
                            ly_yr_gross_amount += value.get('other_ly_yr_gross_amount', 0) or 0

                            lly_yr_retail_amount += value.get('lly_yr_retail_amount', 0) or 0
                            lly_yr_retail_amount += value.get('other_lly_yr_retail_amount', 0) or 0
                            lly_yr_invoice_amount += value.get('lly_yr_invoice_amount', 0) or 0
                            lly_yr_invoice_amount += value.get('other_lly_yr_invoice_amount', 0) or 0
                            lly_yr_gross_amount += value.get('lly_yr_gross_amount', 0) or 0
                            ly_yr_gross_amount += value.get('other_lly_yr_gross_amount', 0) or 0
                        # Commented to Optimise
                        # self._cr.execute(other_sql)
                        # other_result = self._cr.dictfetchall()
                        # for other_value in other_result:
                        #     other_retail_sale += other_value.get('sale_price', 0) or 0
                        #     other_invoice_sale += other_value.get('invoice_price', 0) or 0
                        #     other_gross_margin += other_value.get('gross_margin', 0) or 0
                else:
                    sql = ("""
                        select
                            sum(sm.product_uom_qty)
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as sale_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ( sol.discount)) / 100.0) end) as invoice_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty)  else (sol.price_unit * sm.product_uom_qty)- (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as gross_margin
                            , 0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                            ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            , 0.0 as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.invoice_date >= '%s' and ai.invoice_date <= '%s'
                            and sp.state = 'done' and spt.code='outgoing' and sm.state='done' and sm.product_id = sol.product_id
                            and pt.exclude_from_report != True
                        group by so.id,pt.id,sol.id,sm.id,pp.id
                        UNION ALL
                        select
                            sum(sm.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as ly_mnth_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ( sol.discount)) / 100.0) end) as ly_mnth_invoice_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty)  else (sol.price_unit * sm.product_uom_qty)- (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_gross_amount
                            ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            , 0.0 as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.invoice_date >= '%s' and ai.invoice_date <= '%s'
                            and sp.state = 'done' and spt.code='outgoing' and sm.state='done' and sm.product_id = sol.product_id
                            and pt.exclude_from_report != True
                        group by so.id,pt.id,sol.id,sm.id,pp.id
                        UNION ALL
                        select
                            sum(sm.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            ,0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ( sol.discount)) / 100.0) end) as yr_invoice_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty)  else (sol.price_unit * sm.product_uom_qty)- (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.invoice_date >= '%s' and ai.invoice_date <= '%s'
                            and sp.state = 'done' and spt.code='outgoing' and sm.state='done' and sm.product_id = sol.product_id
                            and pt.exclude_from_report != True
                        group by so.id,pt.id,sol.id,sm.id,pp.id
                        UNION ALL
                        select
                            sum(sm.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            ,0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                            ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            ,0.0 as yr_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as ly_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ( sol.discount)) / 100.0) end) as ly_yr_invoice_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty)  else (sol.price_unit * sm.product_uom_qty)- (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.invoice_date >= '%s' and ai.invoice_date <= '%s'
                            and sp.state = 'done' and spt.code='outgoing' and sm.state='done' and sm.product_id = sol.product_id
                            and pt.exclude_from_report != True
                        group by so.id,pt.id,sol.id,sm.id,pp.id
                        UNION ALL
                        select
                            sum(sm.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            ,0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                            ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            ,0.0 as yr_gross_amount
                            , 0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as lly_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ( sol.discount)) / 100.0) end) as lly_yr_invoice_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty)  else (sol.price_unit * sm.product_uom_qty)- (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id)
                        where ai.invoice_date >= '%s' and ai.invoice_date <= '%s'
                            and sp.state = 'done' and spt.code='outgoing' and sm.state='done' and sm.product_id = sol.product_id
                            and pt.exclude_from_report != True
                        group by so.id,pt.id,sol.id,sm.id,pp.id

                        """) % (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
                    self._cr.execute(sql)
                    result = self._cr.dictfetchall()
                    for value in result:
                        retail_sale += value.get('sale_price', 0.00) or 0.00
                        invoice_sale += value.get('invoice_price', 0.00) or 0.00
                        gross_margin += value.get('gross_margin', 0.00) or 0.00
                        ly_mnth_retail_amount += value.get('ly_mnth_retail_amount', 0.00) or 0.00
                        ly_mnth_invoice_amount += value.get('ly_mnth_invoice_amount', 0.00) or 0.00
                        ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0.00) or 0.00
                        yr_retail_amount += value.get('yr_retail_amount', 0.00) or 0.00
                        yr_invoice_amount += value.get('yr_invoice_amount', 0.00) or 0.00
                        yr_gross_amount += value.get('yr_gross_amount', 0.00) or 0.00
                        ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0.00) or 0.00
                        ly_yr_invoice_amount+= value.get('ly_yr_invoice_amount', 0.00) or 0.00
                        ly_yr_gross_amount+= value.get('ly_yr_gross_amount', 0.00) or 0.00
                        
                        lly_yr_retail_amount += value.get('lly_yr_retail_amount', 0.00) or 0.00
                        lly_yr_invoice_amount+= value.get('lly_yr_invoice_amount', 0.00) or 0.00
                        lly_yr_gross_amount+= value.get('lly_yr_gross_amount', 0.00) or 0.00
            else:
                if user_ids:
                    for user_id in user_ids:
                        sql = ("""
                            select
                                sum(sm.product_uom_qty)
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as sale_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as invoice_price
                                ,(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as gross_margin
                                 , 0.0 as ly_mnth_retail_amount
                                , 0.0 as ly_mnth_invoice_amount
                                , 0.0 as ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as ly_yr_retail_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as ly_yr_gross_amount
                                , 0.0 as lly_yr_retail_amount
                                , 0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                            where ai.payment_state in ('paid','in_payment') and 
                                ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and so.user_id = %s 
                                and pt.exclude_from_report !=True
                            group by so.id,pt.id,sol.id,sm.id,pp.id 
                            UNION
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price,
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as ly_mnth_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as ly_mnth_invoice_amount
                                ,(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as ly_yr_retail_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as ly_yr_gross_amount
                                , 0.0 as lly_yr_retail_amount
                                , 0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                            where ai.payment_state in ('paid','in_payment') and 
                                ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and so.user_id = %s 
                                and pt.exclude_from_report !=True
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION
                             select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price,
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                , 0.0 as ly_mnth_retail_amount
                                , 0.0 as ly_mnth_invoice_amount
                                , 0.0 as ly_mnth_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as yr_invoice_amount
                                ,(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_gross_amount
                                ,0.0 as ly_yr_retail_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as ly_yr_gross_amount
                                , 0.0 as lly_yr_retail_amount
                                , 0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                            where ai.payment_state in ('paid','in_payment') and 
                                ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and so.user_id = %s 
                                and pt.exclude_from_report !=True
                            group by so.id,pt.id,sol.id,sm.id,pp.id 
                            UNION
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price,
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                , 0.0 as ly_mnth_retail_amount
                                , 0.0 as ly_mnth_invoice_amount
                                , 0.0 as ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as ly_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as ly_yr_invoice_amount
                                ,(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_gross_amount
                                , 0.0 as lly_yr_retail_amount
                                , 0.0 as lly_yr_invoice_amount
                                ,0.0 as lly_yr_gross_amount

                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                            where ai.payment_state in ('paid','in_payment') and 
                                ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and so.user_id = %s 
                                and pt.exclude_from_report !=True
                            group by so.id,pt.id,sol.id,sm.id,pp.id 
                            UNION
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price,
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                , 0.0 as ly_mnth_retail_amount
                                , 0.0 as ly_mnth_invoice_amount
                                , 0.0 as ly_mnth_gross_amount
                                ,0.0 as yr_retail_amount
                                , 0.0 as yr_invoice_amount
                                , 0.0 as yr_gross_amount
                                ,0.0 as ly_yr_retail_amount
                                , 0.0 as ly_yr_invoice_amount
                                ,0.0 as ly_yr_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) end) as lly_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) end) as lly_yr_invoice_amount
                                ,(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price=0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                            where ai.payment_state in ('paid','in_payment') and 
                                ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and so.user_id = %s 
                                and pt.exclude_from_report !=True
                            group by so.id,pt.id,sol.id,sm.id,pp.id 
                            """) % (date_from, date_to, user_id.id,last_yr_month_start_date,last_yr_date_to,user_id.id,fiscalyear_start_date,date_to,user_id.id,last_yr_fiscalyear_start_date,last_yr_date_to,user_id.id,llyr_date_from,llyr_date_to,user_id.id)

                        other_sql = ("""
                            select
                                sum(sm.product_uom_qty)
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) / so.user_count end) as sale_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as invoice_price
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as gross_margin
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                , 0.0 as other_ly_mnth_gross_amount
                                , 0.0 as other_yr_retail_amount
                                , 0.0 as other_yr_invoice_amount
                                , 0.0 as other_yr_gross_amount,
                                , 0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0,0 as other_ly_yr_gross_amount
                                , 0.0 as other_lly_yr_retail_amount
                                , 0.0 as other_lly_yr_invoice_amount
                                , 0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                            where ai.payment_state in ('paid','in_payment') 
                                and ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and other.res_users_id = %s 
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION
                             select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) / so.user_count end) as other_ly_mnth_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as other_ly_mnth_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as other_ly_mnth_gross_amount
                                , 0.0 as other_yr_retail_amount
                                , 0.0 as other_yr_invoice_amount
                                , 0.0 as other_yr_gross_amount,
                                , 0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0,0 as other_ly_yr_gross_amount
                                , 0.0 as other_lly_yr_retail_amount
                                , 0.0 as other_lly_yr_invoice_amount
                                , 0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                            where ai.payment_state in ('paid','in_payment') 
                                and ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and other.res_users_id = %s 
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION
                             select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                , 0.0 as other_ly_mnth_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) / so.user_count end) as other_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as other_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as other_yr_gross_amount
                                , 0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0,0 as other_ly_yr_gross_amount
                                , 0.0 as other_lly_yr_retail_amount
                                , 0.0 as other_lly_yr_invoice_amount
                                , 0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                            where ai.payment_state in ('paid','in_payment') 
                                and ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and other.res_users_id = %s 
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                , 0.0 as other_ly_mnth_gross_amount
                                , 0.0 as other_yr_retail_amount
                                , 0.0 as other_yr_invoice_amount
                                , 0.0 as other_yr_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) / so.user_count end) as other_ly_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as other_ly_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as other_ly_yr_gross_amount
                                , 0.0 as other_lly_yr_retail_amount
                                , 0.0 as other_lly_yr_invoice_amount
                                , 0.0 as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                            where ai.payment_state in ('paid','in_payment') 
                                and ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and other.res_users_id = %s 
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id
                            UNION
                            select
                                sum(sm.product_uom_qty)
                                , 0.0 as sale_price
                                , 0.0 as invoice_price
                                , 0.0 as gross_margin
                                , 0.0 as other_ly_mnth_retail_amount
                                , 0.0 as other_ly_mnth_invoice_amount
                                , 0.0 as other_ly_mnth_gross_amount
                                , 0.0 as other_yr_retail_amount
                                , 0.0 as other_yr_invoice_amount
                                , 0.0 as other_yr_gross_amount
                                , 0.0 as other_ly_yr_retail_amount
                                , 0.0 as other_ly_yr_invoice_amount
                                , 0,0 as other_ly_yr_gross_amount
                                ,(case when pt.list_price = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) / so.user_count end) as other_lly_yr_retail_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * ((sol.discount))) / 100.0) / so.user_count end) as other_lly_yr_invoice_amount
                                ,(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) / so.user_count end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as other_lly_yr_gross_amount
                            from sale_order_line sol
                                inner join sale_order so on (so.id = sol.order_id)
                                inner join res_partner rp on (rp.id = so.partner_id)
                                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                                inner join account_move ai on (ai.id = ail.move_id)
                                inner join product_product pp on (sol.product_id = pp.id)
                                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                                inner join product_category pc on (pc.id = pt.categ_id) 
                                inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                            where ai.payment_state in ('paid','in_payment') 
                                and ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and other.res_users_id = %s 
                                and pt.exclude_from_report !=True 
                            group by so.id,pt.id,sol.id,sm.id,pp.id

                            """) % (date_from, date_to, user_id.id,last_yr_month_start_date,last_yr_date_to,user_id.id,fiscalyear_start_date,date_to,user_id.id,last_yr_fiscalyear_start_date,last_yr_date_to,user_id.id,llyr_date_from,llyr_date_to,user_id.id)
                        self._cr.execute(sql)
                        result = self._cr.dictfetchall()
                        for value in result:
                            retail_sale += value.get('sale_price', 0.00) or 0.00
                            invoice_sale += value.get('invoice_price', 0.00) or 0.00
                            gross_margin += value.get('gross_margin', 0.00) or 0.00
                            ly_mnth_retail_amount += value.get('ly_mnth_retail_amount', 0.00) or 0.00
                            ly_mnth_invoice_amount += value.get('ly_mnth_invoice_amount', 0.00) or 0.00
                            ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0.00) or 0.00
                            yr_retail_amount += value.get('yr_retail_amount', 0.00) or 0.00
                            yr_invoice_amount += value.get('yr_invoice_amount', 0.00) or 0.00
                            yr_gross_amount += value.get('yr_gross_amount', 0.00) or 0.00
                            ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0.00) or 0.00
                            ly_yr_invoice_amount += value.get('ly_yr_invoice_amount', 0.00) or 0.00
                            ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0.00) or 0.00
                        self._cr.execute(other_sql)
                        other_result = self._cr.dictfetchall()
                        for other_value in other_result:
                            other_retail_sale += other_value.get('sale_price', 0.00) or 0.00
                            other_invoice_sale += other_value.get('invoice_price', 0.00) or 0.00
                            other_gross_margin += other_value.get('gross_margin', 0.00) or 0.00
                            other_ly_mnth_retail_amount+= other_value.get('other_ly_mnth_retail_amount', 0.00) or 0.00
                            other_ly_mnth_invoice_amount += other_value.get('other_ly_mnth_invoice_amount', 0.00) or 0.00
                            other_ly_mnth_gross_amount += other_value.get('other_ly_mnth_gross_amount', 0.00) or 0.00
                            other_yr_retail_amount += other_value.get('other_yr_retail_amount', 0.00) or 0.00
                            other_yr_invoice_amount += other_value.get('other_yr_invoice_amount', 0.00) or 0.00
                            other_yr_gross_amount += other_value.get('other_yr_gross_amount', 0.00) or 0.00
                            other_ly_yr_retail_amount += other_value.get('other_ly_yr_retail_amount', 0.00) or 0.00
                            other_ly_yr_invoice_amount += other_value.get('other_ly_yr_invoice_amount', 0.00) or 0.00
                            other_ly_yr_gross_amount += other_value.get('other_ly_yr_gross_amount', 0.00) or 0.00
                else:
                    sql = ("""
                        select
                            sum(sol.product_uom_qty)
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as sale_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0) end) as invoice_price
                            ,(case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as cost_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as gross_margin
                            , 0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                            ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            , 0.0 as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount

                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id) 
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id,pt.id,sol.id,sm.id,pp.id 
                        UNION
                        select
                            sum(sol.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as ly_mnth_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0) end) as ly_mnth_invoice_amount
                            ,(case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as cost_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_mnth_gross_amount
                            ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            , 0.0 as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id) 
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id,pt.id,sol.id,sm.id,pp.id 
                        UNION
                        select
                            sum(sol.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            , 0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0) end) as yr_invoice_amount
                            ,(case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as cost_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id) 
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id,pt.id,sol.id,sm.id,pp.id 
                        UNION 
                        select
                            sum(sol.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            , 0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                             ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            , 0.0 as yr_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as ly_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0) end) as ly_yr_invoice_amount
                            ,(case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as cost_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_yr_gross_amount
                            , 0.0 as lly_yr_retail_amount
                            , 0.0 as lly_yr_invoice_amount
                            ,0.0 as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id) 
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id,pt.id,sol.id,sm.id,pp.id
                        UNION
                        select
                            sum(sol.product_uom_qty)
                            , 0.0 as sale_price
                            , 0.0 as invoice_price
                            , 0.0 as gross_margin
                            , 0.0 as ly_mnth_retail_amount
                            , 0.0 as ly_mnth_invoice_amount
                            , 0.0 as ly_mnth_gross_amount
                             ,0.0 as yr_retail_amount
                            , 0.0 as yr_invoice_amount
                            , 0.0 as yr_gross_amount
                            ,0.0 as ly_yr_retail_amount
                            , 0.0 as ly_yr_invoice_amount
                            ,0.0 as ly_yr_gross_amount
                            ,(case when pt.list_price = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) end) as lly_yr_retail_amount
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * ((sol.discount))) / 100.0) end) as lly_yr_invoice_amount
                            ,(case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as cost_price
                            ,(case when sol.discount = 0.0 then (sol.price_unit * sol.product_uom_qty) else (sol.price_unit * sol.product_uom_qty) - (((sol.price_unit * sol.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as lly_yr_gross_amount
                        from sale_order_line sol
                            inner join sale_order so on (so.id = sol.order_id)
                            inner join res_partner rp on (rp.id = so.partner_id)
                            inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                            inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                            inner join account_move ai on (ai.id = ail.move_id)
                            inner join product_product pp on (sol.product_id = pp.id)
                            inner join product_template pt on (pp.product_tmpl_id = pt.id)
                            inner join product_category pc on (pc.id = pt.categ_id) 
                        where ai.payment_state in ('paid','in_payment') 
                            and ai.invoice_date >= '%s' 
                            and ai.invoice_date <= '%s' 
                            and so.user_id = %s 
                            and pt.exclude_from_report !=True 
                        group by so.id,pt.id,sol.id,sm.id,pp.id

                        """) %  (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
                    self._cr.execute(sql)
                    result = self._cr.dictfetchall()
                    for value in result:
                            retail_sale += value.get('sale_price', 0.00) or 0.00
                            invoice_sale += value.get('invoice_price', 0.00) or 0.00
                            gross_margin += value.get('gross_margin', 0.00) or 0.00
                            ly_mnth_retail_amount += value.get('ly_mnth_retail_amount', 0.00) or 0.00
                            ly_mnth_invoice_amount += value.get('ly_mnth_invoice_amount', 0.00) or 0.00
                            ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0.00) or 0.00
                            yr_retail_amount += value.get('yr_retail_amount', 0.00) or 0.00
                            yr_invoice_amount += value.get('yr_invoice_amount', 0.00) or 0.00
                            yr_gross_amount += value.get('yr_gross_amount', 0.00) or 0.00
                            ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0.00) or 0.00
                            ly_yr_invoice_amount += value.get('ly_yr_invoice_amount', 0.00) or 0.00
                            ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0.00) or 0.00
                            ly_yr_retail_amount += value.get('ly_yr_retail_amount', 0.00) or 0.00
                            ly_yr_invoice_amount += value.get('ly_yr_invoice_amount', 0.00) or 0.00
                            ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0.00) or 0.00
        return retail_sale + other_retail_sale, invoice_sale + other_retail_sale, gross_margin + other_gross_margin,ly_mnth_retail_amount+other_ly_mnth_retail_amount,ly_mnth_invoice_amount+other_ly_mnth_invoice_amount,ly_mnth_gross_amount + other_ly_mnth_gross_amount,yr_retail_amount+ other_yr_retail_amount,yr_invoice_amount+ other_yr_invoice_amount,yr_gross_amount + other_yr_gross_amount,ly_yr_retail_amount + other_ly_yr_retail_amount,ly_yr_invoice_amount + other_ly_yr_invoice_amount,ly_yr_gross_amount + other_ly_yr_gross_amount,lly_yr_retail_amount + other_lly_yr_retail_amount,lly_yr_invoice_amount + other_lly_yr_invoice_amount,lly_yr_gross_amount + other_lly_yr_gross_amount

    def get_sale_amount_of_pos(self, date_from, date_to, salesperson_ids, sale_type='sale', check_delivery=None):

        context = self.env.context

        sp_ids = context.get('user_ids', [])
        salesperson_str = ','.join(str(x) for x in salesperson_ids)

        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

        retail_sale = 0
        invoice_sale = 0
        gross_margin = 0
        other_retail_sale = 0
        other_invoice_sale = 0
        other_gross_margin = 0

        if sp_ids:
            for sp in sp_ids:
                # Search to Query converted to optimise
                # pos_order_line = self.env['pos.order.line'].search([
                #     ('order_id.session_id.stop_at', '>=', date_from),
                #     ('order_id.session_id.stop_at', '<=', date_to),
                #     ('order_id.employee_id.user_id', '=', sp.id),
                #     ('product_id.categ_id.sale_type', '=', sale_type), ])
                #
                sql = ("""
                        select psol.id
                        from pos_order_line psol
                            Inner join pos_order pso on (pso.id = psol.order_id)
                            inner join pos_session ps on (ps.id = pso.session_id)
                            inner join hr_employee he on (he.id = pso.employee_id)
                            inner join res_users ru on (ru.id = he.user_id)
                            inner join product_product pp on (pp.id = psol.product_id)
                            inner join product_template pt on (pt.id = pp.product_tmpl_id)
                            inner join product_category pc on (pt.categ_id = pc.id)
                        where
                            ps.stop_at >= '%s'
                            and ps.start_at <= '%s'
                            and he.user_id = %s
                        group by psol.id, pso.id, ps.id, he.id, ru.id, pp.id, pt.id, pc.id
                        """) % (date_from, date_to, sp.id)
                self._cr.execute(sql)
                result = self._cr.dictfetchall()
                pos_order_lines = self.env['pos.order.line'].browse([dict['id'] for dict in result])

                if pos_order_lines:
                    for order_line in pos_order_lines:
                        if order_line.order_id.users_count > 1:
                            if order_line.qty > 0:
                                retail_sale += (order_line.price_unit * order_line.qty) / order_line.order_id.users_count
                                invoice_sale += order_line.price_subtotal / order_line.order_id.users_count
                                gross_margin += ((order_line.price_subtotal) - (
                                        order_line.product_id.standard_price * order_line.qty)) / order_line.order_id.users_count
                        else:
                            if order_line.qty > 0:
                                retail_sale += (order_line.price_unit * order_line.qty)
                                invoice_sale += order_line.price_subtotal
                                gross_margin += order_line.price_subtotal - (
                                        order_line.product_id.standard_price * order_line.qty)

                # Search to Query converted to optimise
                # other_pos_order_line = self.env['pos.order.line'].search(
                #     [('order_id.session_id.stop_at', '>=', date_from),
                #      ('order_id.session_id.stop_at', '<=', date_to),
                #      ('order_id.other_users', 'in', sp.id),
                #      ('product_id.categ_id.sale_type', '=', sale_type),
                #      ])
                #
                sql = ("""
                    select psol.id
                    from pos_order_line psol
                        Inner join pos_order pso on (pso.id = psol.order_id)
                        inner join pos_session ps on (ps.id = pso.session_id)
                        inner join product_product pp on (pp.id = psol.product_id)
                        inner join product_template pt on (pt.id = pp.product_tmpl_id)
                        inner join product_category pc on (pt.categ_id = pc.id)
                    where 
                        ps.stop_at >= '%s'
                        and ps.start_at <= '%s'
                        and %s in (select res_users_id from pos_order_res_users_rel where pos_order_id=pso.id)
                    group by psol.id, pso.id, ps.id, pp.id, pt.id, pc.id
                    """) % (date_from, date_to, sp.id)
                self._cr.execute(sql)
                result = self._cr.dictfetchall()

                other_pos_order_lines = self.env['pos.order.line'].browse([dict['id'] for dict in result])

                for other_order_line in other_pos_order_lines:
                    if other_order_line.order_id.users_count > 1:
                        if other_order_line.qty > 0:
                            other_retail_sale += (other_order_line.product_id.lst_price * other_order_line.qty
                                                  ) / other_order_line.order_id.users_count
                            other_invoice_sale += other_order_line.price_subtotal / other_order_line.order_id.users_count
                            other_gross_margin += ((other_order_line.price_unit * other_order_line.qty) - (
                                    other_order_line.product_id.standard_price * other_order_line.qty)
                                                   ) / other_order_line.order_id.users_count
        else:
            # Search to Query converted to optimise
            # pos_order_line = self.env['pos.order.line'].search([
            #     ('order_id.session_id.stop_at', '>=', date_from),
            #     ('order_id.session_id.stop_at', '<=', date_to),
            #     ('product_id.categ_id.sale_type', '=', sale_type), ])
            # pos_order_line = list(set(pos_order_line))
            #
            sql = ("""
                select psol.id
                from pos_order_line psol
                    Inner join pos_order pso on (pso.id = psol.order_id)
                    inner join pos_session ps on (ps.id = pso.session_id)
                    inner join product_product pp on (pp.id = psol.product_id)
                    inner join product_template pt on (pt.id = pp.product_tmpl_id)
                    inner join product_category pc on (pt.categ_id = pc.id)
                where 
                    ps.stop_at >= '%s'
                    and ps.start_at <= '%s'
                group by psol.id, pso.id, ps.id, pp.id, pt.id, pc.id
                """) % (date_from, date_to)
            self._cr.execute(sql)
            result = self._cr.dictfetchall()

            pos_order_line = self.env['pos.order.line'].browse([dict['id'] for dict in result])

            for order_line in pos_order_line:
                if order_line.qty > 0:
                    retail_sale += (order_line.price_unit * order_line.qty)
                    invoice_sale += order_line.price_subtotal
                    gross_margin += ((order_line.price_subtotal) - (
                            order_line.product_id.standard_price * order_line.qty))

        return retail_sale + other_retail_sale, invoice_sale + other_invoice_sale, gross_margin + other_gross_margin

    def get_disc_amount(self, date_from, date_to, salesperson_ids, sale_type='sale', check_delivery=None):
        ids = ''
        context = self.env.context
        salesperson = context.get('users_ids', [])
        if salesperson:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        account = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)
                , ('code', '=', '450000')])
        discount = 0

        if salesperson:
            for sp in salesperson_ids:
                for ctx_sp in salesperson:
                    if ctx_sp.id == sp:
                        disc_sql = ("""
                            select 
                                ((sum(aml.debit) - sum(aml.credit)) / so.user_count) as sale_price,
                                so.user_count as so_usr_count
                            from sale_order_line sol
                                INNER join sale_order so on (so.id = sol.order_id)
                                INNER join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                                FULL OUTER join account_move_line aml on (aml.id = solir.invoice_line_id)
                                FULL OUTER join account_move ai on (ai.id = aml.move_id)
                                FULL OUTER join res_users_sale_order_rel usrso on (usrso.sale_order_id=so.id)
                            where ai.state in ('posted') 
                                and aml.account_id = %s 
                                and ai.invoice_date >= '%s' 
                                and ai.invoice_date <= '%s' 
                                and (so.user_id = %s or usrso.res_users_id = %s)
                            GROUP BY so.id
                            """) % (account.id, date_from, date_to, sp, sp)

                        disc_pos_sql = ("""
                            select 
                                ((sum(aml.debit) - sum(aml.credit)) / po.users_count) as sale_price,
                                po.users_count as pos_user_count
                            from pos_order po
                                inner join pos_session ps on (ps.id = po.session_id)
                                inner join account_move ai on (ai.id = ps.move_id)
                                inner join account_move_line aml on (ai.id = aml.move_id)
                                full outer join pos_order_res_users_rel posusr on (posusr.pos_order_id = po.id)
                                INNER JOIN hr_employee he on(he.id = po.employee_id)
                                INNER JOIN res_users ru on(ru.id = he.user_id)
                            where aml.parent_state in ('posted') 
                                and aml.account_id = %s 
                                and ai.date >= '%s' 
                                and ai.date <= '%s' 
                                and (ru.id = %s or posusr.res_users_id = %s)
                            GROUP BY po.id
                            """) % (account.id, date_from, date_to, sp, sp)
                        self._cr.execute(disc_sql)
                        so_result = self._cr.dictfetchall()
                        for value in so_result:
                            discount += (value.get('sale_price', 0)) or 0
                        self._cr.execute(disc_pos_sql)
                        pos_result = self._cr.dictfetchall()
                        for value in pos_result:
                            discount += (value.get('sale_price', 0)) or 0
        else:
            sql = ("""
                select (sum(aml.credit) - sum(aml.debit)) as discount
                from account_move_line aml
                    inner join account_move ai on (ai.id = aml.move_id)
                where aml.parent_state in ('posted') and aml.account_id = %s and
                    aml.date >= '%s' and aml.date <= '%s'
                """) % (account.id, date_from, date_to)
            self._cr.execute(sql)
            result = self._cr.dictfetchall()
            discount = 0
            for value in result:
                discount += value.get('discount', 0) or 0
        return discount

    def get_so_return_amount(self, salesperson_ids,date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date,llyr_date_from,llyr_date_to):
        context = self.env.context
        sp_ids =context.get('user_ids')
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        last_yr_month_start_date = datetime.strptime(last_yr_month_start_date, "%Y-%m-%d").date()
        last_yr_date_to = datetime.strptime(last_yr_date_to, "%Y-%m-%d").date()
        fiscalyear_start_date = datetime.strptime(fiscalyear_start_date, "%Y-%m-%d").date()
        llyr_date_from = datetime.strptime(llyr_date_from, "%Y-%m-%d").date()
        llyr_date_to = datetime.strptime(llyr_date_to, "%Y-%m-%d").date()

        sale_type = 'sale'

        mnth_so_return_amount = 0.00
        mnth_so_return_cost = 0.00
        mnth_so_return_gross_amount = 0.00
        ly_mnth_so_return_amount = 0.00
        ly_mnth_so_return_cost = 0.00
        ly_so_return_gross_amount = 0.00
        yr_so_return_amount = 0.00
        yr_so_return_cost = 0.00
        yr_so_return_gross_amount = 0.00
        ly_yr_so_return_amount = 0.00
        ly_yr_so_return_cost = 0.00
        ly_yr_so_return_gross_amount = 0.00
        lly_yr_so_return_amount = 0.00
        lly_yr_so_return_cost = 0.00
        lly_yr_so_return_gross_amount = 0.00

        if sp_ids:
            for sp in sp_ids:
                sql = ("""
                    select sum(case when sol.price_unit = 0.0 then 0
                         else (sol.price_unit*sm.product_uom_qty) end) as sale_price    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (
                        ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (
                        pp.std_price * sm.product_uom_qty) end) as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        , 0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and so.user_id = %s
                        and pt.exclude_from_report !=True 
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                    UNION ALL
                     select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,sum(case when sol.price_unit = 0.0 then 0
                         else (sol.price_unit*sm.product_uom_qty) end) as ly_mnth_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (
                        ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (
                        pp.std_price * sm.product_uom_qty) end) as ly_so_return_gross_amount
                        , 0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and so.user_id = %s
                        and pt.exclude_from_report !=True  
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                    UNION ALL
                     select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        ,sum(case when sol.price_unit = 0.0 then 0
                         else (sol.price_unit*sm.product_uom_qty) end) as yr_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (
                        ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (
                        pp.std_price * sm.product_uom_qty) end) as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and so.user_id = %s
                        and pt.exclude_from_report !=True 
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                     UNION ALL
                     select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        ,0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        ,sum(case when sol.price_unit = 0.0 then 0
                         else (sol.price_unit*sm.product_uom_qty) end) as ly_yr_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (
                        ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (
                        pp.std_price * sm.product_uom_qty) end) as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and so.user_id = %s
                        and pt.exclude_from_report !=True  
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                     UNION ALL
                     select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        ,0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        ,sum(case when sol.price_unit = 0.0 then 0
                         else (sol.price_unit*sm.product_uom_qty) end) as lly_yr_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (
                        ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (
                        pp.std_price * sm.product_uom_qty) end) as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and so.user_id = %s
                        and pt.exclude_from_report !=True 
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)

                    """) %(date_from, date_to, sp.id,last_yr_month_start_date,last_yr_date_to,sp.id,fiscalyear_start_date,date_to,sp.id,last_yr_fiscalyear_start_date,last_yr_date_to,sp.id,llyr_date_from,llyr_date_to,sp.id)
                self._cr.execute(sql)
                res = self._cr.dictfetchall()
                for value in res:
                    mnth_so_return_amount += value.get('sale_price', 0.00) or 0.00
                    mnth_so_return_cost += value.get('cost_price', 0.00) or 0.00
                    mnth_so_return_gross_amount += value.get('gross_margin', 0.00) or 0.00
                    ly_mnth_so_return_amount += value.get('ly_mnth_so_return_amount', 0.00) or 0.00
                    ly_mnth_so_return_cost += value.get('ly_mnth_so_return_cost', 0.00) or 0.00
                    ly_so_return_gross_amount += value.get('ly_so_return_gross_amount', 0.00) or 0.00
                    yr_so_return_amount += value.get('yr_so_return_amount', 0.00) or 0.00
                    yr_so_return_cost += value.get('yr_so_return_cost', 0.00) or 0.00
                    yr_so_return_gross_amount += value.get('yr_so_return_gross_amount', 0.00) or 0.00
                    ly_yr_so_return_amount += value.get('ly_yr_so_return_amount', 0.00) or 0.00
                    ly_yr_so_return_cost += value.get('ly_yr_so_return_cost', 0.00) or 0.00
                    ly_yr_so_return_gross_amount += value.get('ly_yr_so_return_gross_amount', 0.00) or 0.00
                    lly_yr_so_return_amount += value.get('lly_yr_so_return_amount', 0.00) or 0.00
                    lly_yr_so_return_cost += value.get('lly_yr_so_return_cost', 0.00) or 0.00
                    lly_yr_so_return_gross_amount += value.get('lly_yr_so_return_gross_amount', 0.00) or 0.00


                other_sql = ("""
                    select 
                        sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit*sm.product_uom_qty) / so.user_count end) as sale_price    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as cost_price
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else ((sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0)/so.user_count) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        , 0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and other.res_users_id = %s
                        and pt.exclude_from_report !=True 
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                    UNION ALL
                    select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit*sm.product_uom_qty) / so.user_count end) as ly_mnth_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as ly_mnth_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else ((sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0)/so.user_count) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as ly_so_return_gross_amount                      
                        , 0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and other.res_users_id = %s
                        and pt.exclude_from_report !=True 
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                    UNION ALL
                    select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit*sm.product_uom_qty) / so.user_count end) as yr_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as yr_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else ((sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0)/so.user_count) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and other.res_users_id = %s
                        and pt.exclude_from_report !=True  
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                     UNION ALL
                    select 
                         0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        , 0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit*sm.product_uom_qty) / so.user_count end) as ly_yr_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as ly_yr_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else ((sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0)/so.user_count) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as ly_yr_so_return_gross_amount
                        , 0.0 as lly_yr_so_return_amount
                        , 0.0 as lly_yr_so_return_cost 
                        , 0.0 as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and other.res_users_id = %s
                        and pt.exclude_from_report !=True 
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                    UNION ALL
                    select 
                          0.0 as  sale_price
                        , 0.0 as cost_price
                        ,0.0 as gross_margin
                        ,0.0 as ly_mnth_so_return_amount 
                        ,0.0 as ly_mnth_so_return_cost
                        , 0.0 as ly_so_return_gross_amount 
                        , 0.0 as yr_so_return_amount
                        , 0.0 as yr_so_return_cost
                        , 0.0 as yr_so_return_gross_amount
                        , 0.0 as ly_yr_so_return_amount
                        , 0.0 as ly_yr_so_return_cost
                        , 0.0 as ly_yr_so_return_gross_amount
                        ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit*sm.product_uom_qty) / so.user_count end) as lly_yr_so_return_amount    
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as lly_yr_so_return_cost
                        ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) / so.user_count else ((sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0)/so.user_count) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) / so.user_count end) as lly_yr_so_return_gross_amount
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id) 
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code='incoming' 
                        and sm.state='done'
                        and sm.product_id = sol.product_id 
                        and other.res_users_id = %s
                        and pt.exclude_from_report !=True  
                        and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                    """) % (date_from, date_to, sp.id,last_yr_month_start_date,last_yr_date_to,sp.id,fiscalyear_start_date,date_to,sp.id,last_yr_fiscalyear_start_date,last_yr_date_to,sp.id,llyr_date_from,llyr_date_to,sp.id)
                self._cr.execute(other_sql)
                other_res = self._cr.dictfetchall()
                for other_value in other_res:
                    mnth_so_return_amount += other_value.get('sale_price', 0.00) or 0.00
                    mnth_so_return_cost += other_value.get('cost_price', 0.00) or 0.00
                    mnth_so_return_gross_amount += other_value.get('gross_margin', 0.00) or 0.00
                    ly_mnth_so_return_amount += other_value.get('ly_mnth_so_return_amount', 0.00) or 0.00
                    ly_mnth_so_return_cost += other_value.get('ly_mnth_so_return_cost', 0.00) or 0.00
                    ly_so_return_gross_amount += other_value.get('ly_so_return_gross_amount', 0.00) or 0.00
                    yr_so_return_amount += other_value.get('yr_so_return_amount', 0.00) or 0.00
                    yr_so_return_cost += other_value.get('yr_so_return_cost', 0.00) or 0.00
                    yr_so_return_gross_amount += other_value.get('yr_so_return_gross_amount', 0.00) or 0.00
                    ly_yr_so_return_amount += other_value.get('ly_yr_so_return_amount', 0.00) or 0.00
                    ly_yr_so_return_cost += other_value.get('ly_yr_so_return_cost', 0.00) or 0.00
                    ly_yr_so_return_gross_amount += other_value.get('ly_yr_so_return_gross_amount', 0.00) or 0.00
                    lly_yr_so_return_amount += other_value.get('lly_yr_so_return_amount', 0.00) or 0.00
                    lly_yr_so_return_cost += other_value.get('lly_yr_so_return_cost', 0.00) or 0.00
                    lly_yr_so_return_gross_amount += other_value.get('lly_yr_so_return_gross_amount', 0.00) or 0.00


        else:
            sql = ("""
                select 
                    sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit * sm.product_uom_qty) end) as sale_price    
                    ,sum(case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                    ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as gross_margin
                    ,0.0 as ly_mnth_so_return_amount 
                    ,0.0 as ly_mnth_so_return_cost
                    , 0.0 as ly_so_return_gross_amount 
                    , 0.0 as yr_so_return_amount
                    , 0.0 as yr_so_return_cost
                    , 0.0 as yr_so_return_gross_amount
                    , 0.0 as ly_yr_so_return_amount
                    , 0.0 as ly_yr_so_return_cost
                    , 0.0 as ly_yr_so_return_gross_amount
                    , 0.0 as lly_yr_so_return_amount
                    , 0.0 as lly_yr_so_return_cost 
                    , 0.0 as lly_yr_so_return_gross_amount
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='incoming'
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report !=True  
                    and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                UNION ALL
                select 
                     0.0 as  sale_price
                    , 0.0 as cost_price
                    ,0.0 as gross_margin
                    ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit * sm.product_uom_qty) end) as ly_mnth_so_return_amount    
                    ,sum(case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_so_return_cost
                    ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_so_return_gross_amount
                    , 0.0 as yr_so_return_amount
                    , 0.0 as yr_so_return_cost
                    , 0.0 as yr_so_return_gross_amount
                    , 0.0 as ly_yr_so_return_amount
                    , 0.0 as ly_yr_so_return_cost
                    , 0.0 as ly_yr_so_return_gross_amount
                    , 0.0 as lly_yr_so_return_amount
                    , 0.0 as lly_yr_so_return_cost 
                    , 0.0 as lly_yr_so_return_gross_amount
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='incoming'
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report = False 
                    and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                UNION ALL
                select 
                     0.0 as  sale_price
                    , 0.0 as cost_price
                    ,0.0 as gross_margin
                    ,0.0 as ly_mnth_so_return_amount 
                    ,0.0 as ly_mnth_so_return_cost
                    , 0.0 as ly_so_return_gross_amount 
                    ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit * sm.product_uom_qty) end) as yr_so_return_amount    
                    ,sum(case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_so_return_cost
                    ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_so_return_gross_amount
                    , 0.0 as ly_yr_so_return_amount
                    , 0.0 as ly_yr_so_return_cost
                    , 0.0 as ly_yr_so_return_gross_amount
                    , 0.0 as lly_yr_so_return_amount
                    , 0.0 as lly_yr_so_return_cost 
                    , 0.0 as lly_yr_so_return_gross_amount
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='incoming'
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report !=True 
                    and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                 UNION ALL
                select 
                     0.0 as  sale_price
                    , 0.0 as cost_price
                    ,0.0 as gross_margin
                    ,0.0 as ly_mnth_so_return_amount 
                    ,0.0 as ly_mnth_so_return_cost
                    , 0.0 as ly_so_return_gross_amount
                    , 0.0 as yr_so_return_amount
                    , 0.0 as yr_so_return_cost
                    , 0.0 as yr_so_return_gross_amount
                    ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit * sm.product_uom_qty) end) as ly_yr_so_return_amount    
                    ,sum(case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_so_return_cost
                    ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_so_return_gross_amount
                    , 0.0 as lly_yr_so_return_amount
                    , 0.0 as lly_yr_so_return_cost 
                    , 0.0 as lly_yr_so_return_gross_amount
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='incoming'
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report !=True 
                    and (so.partner_id = sp.partner_id or so.partner_id = sp.owner_id)
                 UNION ALL
                select 
                     0.0 as  sale_price
                    , 0.0 as cost_price
                    ,0.0 as gross_margin
                    ,0.0 as ly_mnth_so_return_amount 
                    ,0.0 as ly_mnth_so_return_cost
                    , 0.0 as ly_so_return_gross_amount
                    , 0.0 as yr_so_return_amount
                    , 0.0 as yr_so_return_cost
                    , 0.0 as yr_so_return_gross_amount
                    , 0.0 as ly_yr_so_return_amount
                    , 0.0 as ly_yr_so_return_cost
                    , 0.0 as ly_yr_so_return_gross_amount
                    ,sum(case when sol.price_unit = 0.0 then 0 else (sol.price_unit * sm.product_uom_qty) end) as lly_yr_so_return_amount    
                    ,sum(case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_so_return_cost
                    ,sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else (sol.price_unit * sm.product_uom_qty) - (((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_so_return_gross_amount
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.sale_line_id = sol.id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='incoming'
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report = False 
                    and pt.exclude_from_report !=True 
                """) % (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
            self._cr.execute(sql)
            res = self._cr.dictfetchall()

            for value in res:
                mnth_so_return_amount += value.get('sale_price', 0.00) or 0.00
                mnth_so_return_cost += value.get('cost_price', 0.00) or 0.00
                mnth_so_return_gross_amount += value.get('gross_margin', 0.00) or 0.00
                ly_mnth_so_return_amount += value.get('ly_mnth_so_return_amount', 0.00) or 0.00
                ly_mnth_so_return_cost += value.get('ly_mnth_so_return_cost', 0.00) or 0.00
                ly_so_return_gross_amount += value.get('ly_so_return_gross_amount', 0.00) or 0.00
                yr_so_return_amount += value.get('yr_so_return_amount', 0.00) or 0.00
                yr_so_return_cost += value.get('yr_so_return_cost', 0.00) or 0.00
                yr_so_return_gross_amount += value.get('yr_so_return_gross_amount', 0.00) or 0.00
                ly_yr_so_return_amount += value.get('ly_yr_so_return_amount', 0.00) or 0.00
                ly_yr_so_return_cost += value.get('ly_yr_so_return_cost', 0.00) or 0.00
                ly_yr_so_return_gross_amount += value.get('ly_yr_so_return_gross_amount', 0.00) or 0.00
                lly_yr_so_return_amount += value.get('lly_yr_so_return_amount', 0.00) or 0.00
                lly_yr_so_return_cost += value.get('lly_yr_so_return_cost', 0.00) or 0.00
                lly_yr_so_return_gross_amount += value.get('lly_yr_so_return_gross_amount', 0.00) or 0.00

        return -abs(mnth_so_return_amount), mnth_so_return_amount - mnth_so_return_cost, mnth_so_return_gross_amount, -abs(ly_mnth_so_return_amount),ly_mnth_so_return_amount - ly_mnth_so_return_cost,ly_so_return_gross_amount, -abs(yr_so_return_amount),yr_so_return_amount - yr_so_return_cost,yr_so_return_gross_amount, -abs(ly_yr_so_return_amount),ly_yr_so_return_amount - ly_yr_so_return_cost,ly_yr_so_return_gross_amount,-abs(lly_yr_so_return_amount), lly_yr_so_return_amount - lly_yr_so_return_cost,lly_yr_so_return_gross_amount


    def get_sale_amount_of_pos_service(self, date_from, date_to, salesperson_ids, sale_type='repair'):
        context = self.env.context
        sp_ids = context.get('users_ids', [])
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

        retail_sale = 0.0
        invoice_sale = 0.0
        gross_margin = 0.0

        other_retail_sale = 0.0
        other_invoice_sale = 0.0
        other_gross_margin = 0.0
        if sp_ids:
            for sp in sp_ids:
                # pos_order_line = self.env['pos.order.line'].search([
                #     ('order_id.session_id.start_at', '>=', date_from),
                #     ('order_id.session_id.stop_at', '<=', date_to),
                #     ('order_id.employee_id.user_id', '=', sp.id),
                #     ('product_id.categ_id.sale_type', '=', sale_type), ])
                # pos_order_line = list(set(pos_order_line))
                #
                total_pos = 0.0

                sql = ("""
                    select psol.id
                    from pos_order_line psol
                        Inner join pos_order pso on (pso.id = psol.order_id)
                        inner join pos_session ps on (ps.id = pso.session_id)
                        inner join hr_employee he on (he.id = pso.employee_id)
                        inner join res_users ru on (ru.id = he.user_id)
                        inner join product_product pp on (pp.id = psol.product_id)
                        inner join product_template pt on (pt.id = pp.product_tmpl_id)
                        inner join product_category pc on (pt.categ_id = pc.id)
                    where
                        ps.stop_at >= '%s'
                        and ps.start_at <= '%s'
                        and he.user_id = %s
                        and pc.sale_type = '%s'       
                    group by psol.id, pso.id, ps.id, he.id, ru.id, pp.id, pt.id, pc.id
                    """) % (date_from, date_to, sp.id, sale_type)
                self._cr.execute(sql)
                result = self._cr.dictfetchall()
                pos_order_lines = self.env['pos.order.line'].browse([dict['id'] for dict in result])
                for order_line in pos_order_lines:
                    if order_line.order_id.users_count > 1:
                        if order_line.qty > 0:
                            retail_sale += (order_line.price_unit * order_line.qty) / order_line.order_id.users_count
                            invoice_sale += order_line.price_subtotal / order_line.order_id.users_count
                            gross_margin += ((order_line.price_subtotal) - (
                                    order_line.product_id.standard_price * order_line.qty)) / order_line.order_id.users_count
                    else:
                        if order_line.qty > 0:
                            retail_sale += (order_line.price_unit * order_line.qty)
                            invoice_sale += order_line.price_subtotal
                            gross_margin += order_line.price_subtotal - (
                                    order_line.product_id.standard_price * order_line.qty)

                # other_pos_order_line = self.env['pos.order.line'].search(
                #     [('order_id.session_id.start_at', '>=', date_from),
                #      ('order_id.session_id.stop_at', '<=', date_to),
                #      ('order_id.other_users', 'in', sp.id),
                #      ('product_id.categ_id.sale_type', '=', sale_type),
                #      ])
                # other_pos_order_line = list(set(other_pos_order_line))
                #
                sql = ("""
                    select psol.id
                    from pos_order_line psol
                        Inner join pos_order pso on (pso.id = psol.order_id)
                        inner join pos_session ps on (ps.id = pso.session_id)
                        inner join product_product pp on (pp.id = psol.product_id)
                        inner join product_template pt on (pt.id = pp.product_tmpl_id)
                        inner join product_category pc on (pt.categ_id = pc.id)
                    where 
                        ps.stop_at >= '%s'
                        and ps.start_at <= '%s'
                        and %s in (select res_users_id from pos_order_res_users_rel where pos_order_id=pso.id)
                        and pc.sale_type = '%s'  
                    group by psol.id, pso.id, ps.id, pp.id, pt.id, pc.id
                    """) % (date_from, date_to, sp.id, sale_type)
                self._cr.execute(sql)
                result = self._cr.dictfetchall()

                other_pos_order_lines = self.env['pos.order.line'].browse([dict['id'] for dict in result])

                for other_order_line in other_pos_order_lines:
                    if other_order_line.order_id.users_count > 1:
                        if other_order_line.qty > 0:
                            other_retail_sale += (
                                                         other_order_line.product_id.lst_price * other_order_line.qty) / other_order_line.order_id.users_count
                            other_invoice_sale += other_order_line.price_subtotal / other_order_line.order_id.users_count
                            other_gross_margin += ((other_order_line.price_unit * other_order_line.qty) - (
                                    other_order_line.product_id.standard_price * other_order_line.qty)) / other_order_line.order_id.users_count
        else:
            # pos_order_line = self.env['pos.order.line'].search([
            #     ('order_id.session_id.start_at', '>=', date_from),
            #     ('order_id.session_id.stop_at', '<=', date_to),
            #     ('product_id.categ_id.sale_type', '=', sale_type), ])
            # pos_order_line = list(set(pos_order_line))
            #
            sql = ("""
                select psol.id
                from pos_order_line psol
                    Inner join pos_order pso on (pso.id = psol.order_id)
                    inner join pos_session ps on (ps.id = pso.session_id)
                    inner join product_product pp on (pp.id = psol.product_id)
                    inner join product_template pt on (pt.id = pp.product_tmpl_id)
                    inner join product_category pc on (pt.categ_id = pc.id)
                where 
                    ps.stop_at >= '%s'
                    and ps.start_at <= '%s'
                    and pc.sale_type = '%s'  
                group by psol.id, pso.id, ps.id, pp.id, pt.id, pc.id
                """) % (date_from, date_to, sale_type)
            self._cr.execute(sql)
            result = self._cr.dictfetchall()

            pos_order_line = self.env['pos.order.line'].browse([dict['id'] for dict in result])

            for order_line in pos_order_line:
                if order_line.order_id.users_count > 1:
                    if order_line.qty > 0:
                        retail_sale += (order_line.price_unit * order_line.qty) / order_line.order_id.users_count
                        invoice_sale += order_line.price_subtotal / order_line.order_id.users_count
                        gross_margin += ((order_line.price_subtotal) - (
                                order_line.product_id.standard_price * order_line.qty)) / order_line.order_id.users_count
                else:
                    if order_line.qty > 0:
                        retail_sale += (order_line.price_unit * order_line.qty)
                        invoice_sale += order_line.price_subtotal
                        gross_margin += order_line.price_subtotal - (
                                order_line.product_id.standard_price * order_line.qty)

        return retail_sale + other_retail_sale, invoice_sale + other_invoice_sale, gross_margin + other_gross_margin

    def get_so_return_amount_of_pos(self, salesperson_ids,date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date,llyr_date_from,llyr_date_to):
        mnth_sales_orders = []
        context = self.env.context
        sp_ids = context.get('user_ids', [])
        salesperson_str = ','.join(str(x) for x in salesperson_ids)
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        last_yr_month_start_date = datetime.strptime(last_yr_month_start_date, "%Y-%m-%d").date()
        last_yr_date_to = datetime.strptime(last_yr_date_to, "%Y-%m-%d").date()
        fiscalyear_start_date = datetime.strptime(fiscalyear_start_date, "%Y-%m-%d").date()
        llyr_date_from = datetime.strptime(llyr_date_from, "%Y-%m-%d").date()
        llyr_date_to = datetime.strptime(llyr_date_to, "%Y-%m-%d").date()
        sale_type = 'sale'
        mnth_so_return_amount = 0
        mnth_so_return_cost_pos = 0
        mnth_so_return_gross_amount = 0
        ly_mnth_so_return_amount_pos = 0
        ly_mnth_so_return_cost_pos = 0
        ly_so_return_gross_amount_pos = 0
        yr_so_return_amount_pos = 0
        yr_so_return_cost_pos = 0
        yr_so_return_gross_amount_pos = 0
        ly_yr_so_return_amount_pos = 0
        ly_yr_so_return_cost_pos = 0
        ly_yr_so_return_gross_amount_pos = 0
        lly_yr_so_return_amount_pos = 0
        lly_yr_so_return_cost_pos = 0
        lly_yr_so_return_gross_amount_pos = 0
        if sp_ids:
            for sp in sp_ids:
                sql = ("""
                    select 
                    sum(case when pol.price_unit = 0.0 then 0 else (pol.price_unit * sm.product_uom_qty) end) as sale_price  
                    ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                    ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
                        else (pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)  
                        end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)  end) as gross_margin
                    ,0 as ly_mnth_so_return_amount_pos
                    ,0 as ly_mnth_so_return_cost_pos
                    ,0 as ly_so_return_gross_amount_pos
                    ,0 as yr_so_return_amount_pos
                    ,0 as yr_so_return_cost_pos
                    ,0 as yr_so_return_gross_amount_pos
                    ,0 as ly_yr_so_return_amount_pos
                    ,0 as ly_yr_so_return_cost_pos
                    ,0 as ly_yr_so_return_gross_amount_pos
                    , 0 as lly_yr_so_return_amount_pos
                    , 0 as lly_yr_so_return_cost_pos
                    , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join hr_employee he on (he.id = po.employee_id)
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming') 
                        and sm.state='done'
                        and he.user_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select 
                      0 as sale_price
                    , 0 as cost_price
                    , 0 as gross_margin
                    ,sum(case when pol.price_unit = 0.0 then 0 else (pol.price_unit * sm.product_uom_qty) end) as ly_mnth_so_return_amount_pos  
                    ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_so_return_cost_pos
                    ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
                        else (pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)  
                        end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)  end) as ly_so_return_gross_amount_pos
                    ,0 as yr_so_return_amount_pos
                    ,0 as yr_so_return_cost_pos
                    ,0 as yr_so_return_gross_amount_pos
                    ,0 as ly_yr_so_return_amount_pos
                    ,0 as ly_yr_so_return_cost_pos
                    ,0 as ly_yr_so_return_gross_amount_pos
                    , 0 as lly_yr_so_return_amount_pos
                    , 0 as lly_yr_so_return_cost_pos
                    , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join hr_employee he on (he.id = po.employee_id)
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming') 
                        and sm.state='done'
                        and he.user_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select 
                      0 as sale_price
                    , 0 as cost_price
                    , 0 as gross_margin
                    ,0 as ly_mnth_so_return_amount_pos
                    ,0 as ly_mnth_so_return_cost_pos
                    ,0 as ly_so_return_gross_amount_pos
                    ,sum(case when pol.price_unit = 0.0 then 0 else (pol.price_unit * sm.product_uom_qty) end) as yr_so_return_amount_pos  
                    ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_so_return_cost_pos
                    ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
                        else (pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)  
                        end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)  end) as yr_so_return_gross_amount_pos
                    ,0 as ly_yr_so_return_amount_pos
                    ,0 as ly_yr_so_return_cost_pos
                    ,0 as ly_yr_so_return_gross_amount_pos
                    , 0 as lly_yr_so_return_amount_pos
                    , 0 as lly_yr_so_return_cost_pos
                    , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join hr_employee he on (he.id = po.employee_id)
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming') 
                        and sm.state='done'
                        and he.user_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select 
                      0 as sale_price
                    , 0 as cost_price
                    , 0 as gross_margin
                    ,0 as ly_mnth_so_return_amount_pos
                    ,0 as ly_mnth_so_return_cost_pos
                    ,0 as ly_so_return_gross_amount_pos
                    ,0 as yr_so_return_amount_pos
                    ,0 as yr_so_return_cost_pos
                    ,0 as yr_so_return_gross_amount_pos
                    ,sum(case when pol.price_unit = 0.0 then 0 else (pol.price_unit * sm.product_uom_qty) end) as ly_yr_so_return_amount_pos  
                    ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_so_return_amount_pos
                    ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
                        else (pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)  
                        end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)  end) as ly_yr_so_return_gross_amount_pos
                    , 0 as lly_yr_so_return_amount_pos
                    , 0 as lly_yr_so_return_cost_pos
                    , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join hr_employee he on (he.id = po.employee_id)
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming') 
                        and sm.state='done'
                        and he.user_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select 
                      0 as sale_price
                    , 0 as cost_price
                    , 0 as gross_margin
                    ,0 as ly_mnth_so_return_amount_pos
                    ,0 as ly_mnth_so_return_cost_pos
                    ,0 as ly_so_return_gross_amount_pos
                    ,0 as yr_so_return_amount_pos
                    ,0 as yr_so_return_cost_pos
                    ,0 as yr_so_return_gross_amount_pos
                    ,0 as ly_yr_so_return_amount_pos
                    ,0 as ly_yr_so_return_cost_pos
                    ,0 as ly_yr_so_return_gross_amount_pos
                    ,sum(case when pol.price_unit = 0.0 then 0 else (pol.price_unit * sm.product_uom_qty) end) as lly_yr_so_return_amount_pos  
                    ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_so_return_cost_pos
                    ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
                        else (pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)  
                        end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)  end) as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join hr_employee he on (he.id = po.employee_id)
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming') 
                        and sm.state='done'
                        and he.user_id = %s and pt.exclude_from_report!=True

                    """) % (date_from, date_to, sp.id,last_yr_month_start_date,last_yr_date_to,sp.id,fiscalyear_start_date,date_to,sp.id,last_yr_fiscalyear_start_date,last_yr_date_to,sp.id,llyr_date_from,llyr_date_to,sp.id)

                self._cr.execute(sql)
                res = self._cr.dictfetchall()

                for value in res:
                    mnth_so_return_amount += value.get('sale_price', 0.00) or 0.00
                    mnth_so_return_cost_pos += value.get('cost_price', 0.00) or 0.00
                    mnth_so_return_gross_amount += value.get('gross_margin', 0.00) or 0.00
                    ly_mnth_so_return_amount_pos += value.get('ly_mnth_so_return_amount_pos', 0.00) or 0.00
                    ly_mnth_so_return_cost_pos += value.get('ly_mnth_so_return_cost_pos', 0.00) or 0.00
                    ly_so_return_gross_amount_pos += value.get('ly_so_return_gross_amount_pos', 0.00) or 0.00
                    yr_so_return_amount_pos += value.get('yr_so_return_amount_pos', 0.00) or 0.00
                    yr_so_return_cost_pos += value.get('yr_so_return_cost_pos', 0.00) or 0.00
                    yr_so_return_gross_amount_pos += value.get('yr_so_return_gross_amount_pos', 0.00) or 0.00
                    ly_yr_so_return_amount_pos += value.get('ly_yr_so_return_amount_pos', 0.00) or 0.00
                    ly_yr_so_return_cost_pos += value.get('ly_yr_so_return_cost_pos', 0.00) or 0.00
                    ly_yr_so_return_gross_amount_pos += value.get('ly_yr_so_return_gross_amount_pos', 0.00) or 0.00
                    lly_yr_so_return_amount_pos += value.get('lly_yr_so_return_amount_pos', 0.00) or 0.00
                    lly_yr_so_return_cost_pos += value.get('lly_yr_so_return_cost_pos', 0.00) or 0.00
                    lly_yr_so_return_gross_amount_pos += value.get('lly_yr_so_return_gross_amount_pos', 0.00) or 0.00

                other_sql = ("""
                    select 
                        sum(case when pol.price_unit = 0.0 then 0
                        else (pol.price_unit*sm.product_uom_qty) /  po.users_count end) as sale_price  
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) /  po.users_count end) as cost_price
                        ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty)/po.users_count 
                            else ((pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)/po.users_count)  
                            end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/po.users_count end) as gross_margin            
                        ,0 as ly_mnth_so_return_amount_pos
                        ,0 as ly_mnth_so_return_cost_pos
                        ,0 as ly_so_return_gross_amount_pos
                        ,0 as yr_so_return_amount_pos
                        ,0 as yr_so_return_cost_pos
                        ,0 as yr_so_return_gross_amount_pos
                        ,0 as ly_yr_so_return_amount_pos
                        ,0 as ly_yr_so_return_cost_pos
                        ,0 as ly_yr_so_return_gross_amount_pos
                        , 0 as lly_yr_so_return_amount_pos
                        , 0 as lly_yr_so_return_cost_pos
                        , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming')
                        and sm.state='done' 
                        and other.res_users_id = %s and pt.exclude_from_report!=True 
                    UNION ALL
                    select
                        0 as sale_price
                        ,0 as cost_price
                        ,0 as gross_margin
                        ,sum(case when pol.price_unit = 0.0 then 0
                        else (pol.price_unit*sm.product_uom_qty) /  po.users_count end) as ly_mnth_so_return_amount_pos  
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) /  po.users_count end) as ly_mnth_so_return_cost_pos
                        ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty)/po.users_count 
                            else ((pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)/po.users_count)  
                            end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/po.users_count end) as ly_so_return_gross_amount_pos
                        ,0 as yr_so_return_amount_pos
                        ,0 as yr_so_return_cost_pos
                        ,0 as yr_so_return_gross_amount_pos
                        ,0 as ly_yr_so_return_amount_pos
                        ,0 as ly_yr_so_return_cost_pos
                        ,0 as ly_yr_so_return_gross_amount_pos
                        , 0 as lly_yr_so_return_amount_pos
                        , 0 as lly_yr_so_return_cost_pos
                        , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming')
                        and sm.state='done' 
                        and other.res_users_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select
                        0 as sale_price
                        ,0 as cost_price
                        ,0 as gross_margin
                        ,0 as ly_mnth_so_return_amount_pos
                        ,0 as ly_mnth_so_return_cost_pos
                        ,0 as ly_so_return_gross_amount_pos
                        ,sum(case when pol.price_unit = 0.0 then 0
                        else (pol.price_unit*sm.product_uom_qty) /  po.users_count end) as yr_so_return_amount_pos  
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) /  po.users_count end) as yr_so_return_cost_pos
                        ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty)/po.users_count 
                            else ((pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)/po.users_count)  
                            end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/po.users_count end) as yr_so_return_gross_amount_pos
                        ,0 as ly_yr_so_return_amount_pos
                        ,0 as ly_yr_so_return_cost_pos
                        ,0 as ly_yr_so_return_gross_amount_pos
                        , 0 as lly_yr_so_return_amount_pos
                        , 0 as lly_yr_so_return_cost_pos
                        , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming')
                        and sm.state='done' 
                        and other.res_users_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select
                        0 as sale_price
                        ,0 as cost_price
                        ,0 as gross_margin
                        ,0 as ly_mnth_so_return_amount_pos
                        ,0 as ly_mnth_so_return_cost_pos
                        ,0 as ly_so_return_gross_amount_pos
                        ,0 as yr_so_return_amount_pos
                        ,0 as yr_so_return_cost_pos
                        ,0 as yr_so_return_gross_amount_pos
                        ,sum(case when pol.price_unit = 0.0 then 0
                        else (pol.price_unit*sm.product_uom_qty) /  po.users_count end) as ly_yr_so_return_amount_pos  
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) /  po.users_count end) as ly_yr_so_return_cost_pos
                        ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty)/po.users_count 
                            else ((pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)/po.users_count)  
                            end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/po.users_count end) as ly_yr_so_return_gross_amount_pos
                        , 0 as lly_yr_so_return_amount_pos
                        , 0 as lly_yr_so_return_cost_pos
                        , 0 as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming')
                        and sm.state='done' 
                        and other.res_users_id = %s and pt.exclude_from_report!=True
                    UNION ALL
                    select
                        0 as sale_price
                        ,0 as cost_price
                        ,0 as gross_margin
                        ,0 as ly_mnth_so_return_amount_pos
                        ,0 as ly_mnth_so_return_cost_pos
                        ,0 as ly_so_return_gross_amount_pos
                        ,0 as yr_so_return_amount_pos
                        ,0 as yr_so_return_cost_pos
                        ,0 as yr_so_return_gross_amount_pos
                        ,0 as ly_yr_so_return_amount_pos
                        ,0 as ly_yr_so_return_cost_pos
                        ,0 as ly_yr_so_return_gross_amount_pos
                        ,sum(case when pol.price_unit = 0.0 then 0
                        else (pol.price_unit*sm.product_uom_qty) /  po.users_count end) as lly_yr_so_return_amount_pos  
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) /  po.users_count end) as lly_yr_so_return_cost_pos
                        ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty)/po.users_count 
                            else ((pol.price_unit*sm.product_uom_qty)-(((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0)/po.users_count)  
                            end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)/po.users_count end) as lly_yr_so_return_gross_amount_pos
                    from pos_order_line pol
                        inner join pos_order po on (po.id = pol.order_id)

                        inner join stock_picking sp on (sp.pos_order_id = po.id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                        inner join product_product pp on (sm.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('incoming')
                        and sm.state='done' 
                        and other.res_users_id = %s and pt.exclude_from_report!=True
                    """) % (date_from, date_to, sp.id,last_yr_month_start_date,last_yr_date_to,sp.id,fiscalyear_start_date,date_to,sp.id,last_yr_fiscalyear_start_date,last_yr_date_to,sp.id,llyr_date_from,llyr_date_to,sp.id)

                self._cr.execute(other_sql)
                other_res = self._cr.dictfetchall()

                for other_value in other_res:
                    mnth_so_return_amount += other_value.get('sale_price', 0.00) or 0.00
                    mnth_so_return_cost_pos += other_value.get('cost_price', 0.00) or 0.00
                    mnth_so_return_gross_amount += other_value.get('gross_margin', 0.00) or 0.00
                    ly_mnth_so_return_amount_pos += other_value.get('ly_mnth_so_return_amount_pos', 0.00) or 0.00
                    ly_mnth_so_return_cost_pos += other_value.get('ly_mnth_so_return_cost_pos', 0.00) or 0.00
                    ly_so_return_gross_amount_pos += other_value.get('ly_so_return_gross_amount_pos', 0.00) or 0.00
                    yr_so_return_amount_pos += other_value.get('yr_so_return_amount_pos', 0.00) or 0.00
                    yr_so_return_cost_pos += other_value.get('yr_so_return_cost_pos', 0.00) or 0.00
                    yr_so_return_gross_amount_pos += other_value.get('yr_so_return_gross_amount_pos', 0.00) or 0.00
                    ly_yr_so_return_amount_pos += other_value.get('ly_yr_so_return_amount_pos', 0.00) or 0.00
                    ly_yr_so_return_cost_pos += other_value.get('ly_yr_so_return_cost_pos', 0.00) or 0.00
                    ly_yr_so_return_gross_amount_pos += other_value.get('ly_yr_so_return_gross_amount_pos', 0.00) or 0.00
                    lly_yr_so_return_amount_pos += other_value.get('lly_yr_so_return_amount_pos', 0.00) or 0.00
                    lly_yr_so_return_cost_pos += other_value.get('lly_yr_so_return_cost_pos', 0.00) or 0.00
                    lly_yr_so_return_gross_amount_pos += other_value.get('lly_yr_so_return_gross_amount_pos', 0.00) or 0.00

        else:
            sql = ("""
                select 
                sum(case when pol.price_unit = 0.0 then 0
                     else (pol.price_unit*sm.product_uom_qty) end) as sale_price  
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price
                ,sum(case when pol.discount = 0.0 then (pol.price_unit * sm.product_uom_qty) else (
                    pol.price_unit * sm.product_uom_qty) - (((pol.price_unit * sm.product_uom_qty) * (pol.discount)
                    ) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)
                     end) as gross_margin
                ,0 as ly_mnth_so_return_amount_pos
                ,0 as ly_mnth_so_return_cost_pos
                ,0 as ly_so_return_gross_amount_pos
                ,0 as yr_so_return_amount_pos
                ,0 as yr_so_return_cost_pos
                ,0 as yr_so_return_gross_amount_pos
                ,0 as ly_yr_so_return_amount_pos
                ,0 as ly_yr_so_return_cost_pos
                ,0 as ly_yr_so_return_gross_amount_pos
                , 0 as lly_yr_so_return_amount_pos
                , 0 as lly_yr_so_return_cost_pos
                , 0 as lly_yr_so_return_gross_amount_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('incoming') 
                    and sm.state='done'
                    and pt.exclude_from_report !=True 
                UNION ALL
                select 
                  0 as sale_price
                , 0 as cost_price
                , 0 as gross_margin
                ,sum(case when pol.price_unit = 0.0 then 0
                     else (pol.price_unit*sm.product_uom_qty) end) as ly_mnth_so_return_amount_pos  
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_so_return_cost_pos
                ,sum(case when pol.discount = 0.0 then (pol.price_unit * sm.product_uom_qty) else (
                    pol.price_unit * sm.product_uom_qty) - (((pol.price_unit * sm.product_uom_qty) * (pol.discount)
                    ) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)
                     end) as ly_so_return_gross_amount_pos
                ,0 as yr_so_return_amount_pos
                ,0 as yr_so_return_cost_pos
                ,0 as yr_so_return_gross_amount_pos
                ,0 as ly_yr_so_return_amount_pos
                ,0 as ly_yr_so_return_cost_pos
                ,0 as ly_yr_so_return_gross_amount_pos
                , 0 as lly_yr_so_return_amount_pos
                , 0 as lly_yr_so_return_cost_pos
                , 0 as lly_yr_so_return_gross_amount_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('incoming') 
                    and sm.state='done'
                    and pt.exclude_from_report !=True
                 UNION ALL
                select 
                  0 as sale_price
                , 0 as cost_price
                , 0 as gross_margin
                ,0 as ly_mnth_so_return_amount_pos
                ,0 as ly_mnth_so_return_cost_pos
                ,0 as ly_so_return_gross_amount_pos
                ,sum(case when pol.price_unit = 0.0 then 0
                     else (pol.price_unit*sm.product_uom_qty) end) as yr_so_return_amount_pos  
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_so_return_cost_pos
                ,sum(case when pol.discount = 0.0 then (pol.price_unit * sm.product_uom_qty) else (
                    pol.price_unit * sm.product_uom_qty) - (((pol.price_unit * sm.product_uom_qty) * (pol.discount)
                    ) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)
                     end) as yr_so_return_gross_amount_pos
                ,0 as ly_yr_so_return_amount_pos
                ,0 as ly_yr_so_return_cost_pos
                ,0 as ly_yr_so_return_gross_amount_pos
                , 0 as lly_yr_so_return_amount_pos
                , 0 as lly_yr_so_return_cost_pos
                , 0 as lly_yr_so_return_gross_amount_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('incoming') 
                    and sm.state='done'
                    and pt.exclude_from_report !=True 
                UNION ALL
                select 
                  0 as sale_price
                , 0 as cost_price
                , 0 as gross_margin
                ,0 as ly_mnth_so_return_amount_pos
                ,0 as ly_mnth_so_return_cost_pos
                ,0 as ly_so_return_gross_amount_pos
                ,0 as yr_so_return_amount_pos
                ,0 as yr_so_return_cost_pos
                ,0 as yr_so_return_gross_amount_pos
                ,sum(case when pol.price_unit = 0.0 then 0
                     else (pol.price_unit*sm.product_uom_qty) end) as ly_yr_so_return_amount_pos  
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_so_return_cost_pos
                ,sum(case when pol.discount = 0.0 then (pol.price_unit * sm.product_uom_qty) else (
                    pol.price_unit * sm.product_uom_qty) - (((pol.price_unit * sm.product_uom_qty) * (pol.discount)
                    ) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)
                     end) as ly_yr_so_return_gross_amount_pos
                , 0 as lly_yr_so_return_amount_pos
                , 0 as lly_yr_so_return_cost_pos
                , 0 as lly_yr_so_return_gross_amount_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('incoming') 
                    and sm.state='done'
                    and pt.exclude_from_report !=True
                 UNION ALL
                select 
                  0 as sale_price
                , 0 as cost_price
                , 0 as gross_margin
                ,0 as ly_mnth_so_return_amount_pos
                ,0 as ly_mnth_so_return_cost_pos
                ,0 as ly_so_return_gross_amount_pos
                ,0 as yr_so_return_amount_pos
                ,0 as yr_so_return_cost_pos
                ,0 as yr_so_return_gross_amount_pos
                ,0 as ly_yr_so_return_amount_pos
                ,0 as ly_yr_so_return_cost_pos
                ,0 as ly_yr_so_return_gross_amount_pos
                ,sum(case when pol.price_unit = 0.0 then 0
                     else (pol.price_unit*sm.product_uom_qty) end) as lly_yr_so_return_amount_pos  
                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as lly_yr_so_return_cost_pos
                ,sum(case when pol.discount = 0.0 then (pol.price_unit * sm.product_uom_qty) else (
                    pol.price_unit * sm.product_uom_qty) - (((pol.price_unit * sm.product_uom_qty) * (pol.discount)
                    ) / 100.0) end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty)
                     end) as lly_yr_so_return_gross_amount_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id and sm.product_id = pol.product_id )
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and spt.code in ('incoming') 
                    and sm.state='done'
                    and pt.exclude_from_report !=True 
                """) % (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
            self._cr.execute(sql)
            res = self._cr.dictfetchall()
            for value in res:
                mnth_so_return_amount += value.get('sale_price', 0.00) or 0.00
                mnth_so_return_cost_pos += value.get('cost_price', 0.00) or 0.00
                mnth_so_return_gross_amount += value.get('gross_margin', 0.00) or 0.00
                ly_mnth_so_return_amount_pos += value.get('ly_mnth_so_return_amount_pos', 0.00) or 0.00
                ly_mnth_so_return_cost_pos += value.get('ly_mnth_so_return_cost_pos', 0.00) or 0.00
                ly_so_return_gross_amount_pos += value.get('ly_so_return_gross_amount_pos', 0.00) or 0.00
                yr_so_return_amount_pos += value.get('yr_so_return_amount_pos', 0.00) or 0.00
                yr_so_return_cost_pos += value.get('yr_so_return_cost_pos', 0.00) or 0.00
                yr_so_return_gross_amount_pos += value.get('yr_so_return_gross_amount_pos', 0.00) or 0.00
                ly_yr_so_return_amount_pos += value.get('ly_yr_so_return_amount_pos', 0.00) or 0.00
                ly_yr_so_return_cost_pos += value.get('ly_yr_so_return_cost_pos', 0.00) or 0.00
                ly_yr_so_return_gross_amount_pos += value.get('ly_yr_so_return_gross_amount_pos', 0.00) or 0.00
                lly_yr_so_return_amount_pos += value.get('lly_yr_so_return_amount_pos', 0.00) or 0.00
                lly_yr_so_return_cost_pos += value.get('lly_yr_so_return_cost_pos', 0.00) or 0.00
                lly_yr_so_return_gross_amount_pos += value.get('lly_yr_so_return_gross_amount_pos', 0.00) or 0.00
        return -abs(mnth_so_return_amount), mnth_so_return_amount - mnth_so_return_cost_pos, mnth_so_return_gross_amount, -abs(ly_mnth_so_return_amount_pos), ly_mnth_so_return_amount_pos - ly_mnth_so_return_cost_pos,ly_so_return_gross_amount_pos, -abs(yr_so_return_amount_pos), yr_so_return_amount_pos - yr_so_return_cost_pos,yr_so_return_gross_amount_pos, -abs(ly_yr_so_return_amount_pos), ly_yr_so_return_amount_pos - ly_yr_so_return_cost_pos,ly_yr_so_return_gross_amount_pos,-abs(lly_yr_so_return_amount_pos), lly_yr_so_return_amount_pos - lly_yr_so_return_cost_pos, lly_yr_so_return_gross_amount_pos

    def get_repair_service_lines(self, row_name, sale_type, month_start_date, date_to, last_yr_month_start_date,
                                 last_yr_date_to, fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                                 llyr_date_from):
        context = self.env.context
        user_ids = self.env['res.users']
        if 'options' in context:
            salesperson_ids = self.env['res.users'].browse(context['options']['users_ids'])
            user_ids|=salesperson_ids
        else:
            salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        line_list = []
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids
            (mnth_retail_amount, mnth_invoice_amount,
             mnth_gross_amount, ly_mnth_retail_amount, ly_mnth_invoice_amount, ly_mnth_gross_amount,
               yr_retail_amount, yr_invoice_amount, yr_gross_amount,
               ly_yr_retail_amount, ly_yr_invoice_amount, ly_yr_gross_amount,
               ly_yr_retail_amount, lly_yr_invoice_amount, lly_yr_gross_amount) = self.with_context({'user_ids':user_ids}).get_sale_amount( str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),str(llyr_date_from), str(llyr_date_to), salesperson_ids, sale_type)

            mnth_retail_amount_pos, mnth_invoice_amount_pos, mnth_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos_service(
                str(month_start_date), date_to, salesperson_ids, sale_type)

            mnth_retail_amount = mnth_retail_amount + mnth_retail_amount_pos
            mnth_invoice_amount = mnth_invoice_amount + mnth_invoice_amount_pos
            mnth_gross_amount = mnth_gross_amount + mnth_gross_amount_pos

            mnth_invoice_plan = self.get_planned_values(sale_type + '_sold_amount', month_start_date, date_to,
                                                        salesperson_ids)

            mnth_gross_plan = self.get_planned_values(sale_type + '_gross_amount', month_start_date, date_to,
                                                      salesperson_ids)

            mnth_invoice_perc = mnth_invoice_plan and (mnth_invoice_amount) / mnth_invoice_plan or 0

            # ly_mnth_retail_amount, ly_mnth_invoice_amount, ly_mnth_gross_amount = self.get_sale_amount(
            #     str(last_yr_month_start_date), str(last_yr_date_to), salesperson_ids, sale_type)
            ly_mnth_retail_amount_pos, ly_mnth_invoice_amount_pos, ly_mnth_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos_service(
                str(last_yr_month_start_date), str(last_yr_date_to), salesperson_ids, sale_type)
            ly_mnth_retail_amount = ly_mnth_retail_amount + ly_mnth_retail_amount_pos
            ly_mnth_invoice_amount = ly_mnth_invoice_amount + ly_mnth_invoice_amount_pos
            ly_mnth_gross_amount = ly_mnth_gross_amount + ly_mnth_gross_amount_pos

            mnth_invoice_inc_dec = ly_mnth_invoice_amount and (
                    mnth_invoice_amount - ly_mnth_invoice_amount) / ly_mnth_invoice_amount or 0

            # yr_retail_amount, yr_invoice_amount, yr_gross_amount = self.get_sale_amount(str(fiscalyear_start_date),
            #                                                                             date_to, salesperson_ids,
            #                                                                             sale_type)
            yr_retail_amount_pos, yr_invoice_amount_pos, yr_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos_service(
                str(fiscalyear_start_date), date_to, salesperson_ids, sale_type)
            yr_retail_amount = yr_retail_amount + yr_retail_amount_pos
            yr_invoice_amount = yr_invoice_amount + yr_invoice_amount_pos
            yr_gross_amount = yr_gross_amount + yr_gross_amount_pos

            yr_invoice_plan = self.get_planned_values(sale_type + '_sold_amount', fiscalyear_start_date, date_to,
                                                      salesperson_ids)
            yr_gross_plan = self.get_planned_values(sale_type + '_gross_amount', fiscalyear_start_date, date_to,
                                                    salesperson_ids)

            yr_invoice_perc = yr_invoice_plan and (yr_invoice_amount) / yr_invoice_plan or 0

            # ly_yr_retail_amount, ly_yr_invoice_amount, ly_yr_gross_amount = self.get_sale_amount(
            #     str(last_yr_fiscalyear_start_date), str(last_yr_date_to), salesperson_ids, sale_type)

            (ly_yr_retail_amount_pos, ly_yr_invoice_amount_pos,
             ly_yr_gross_amount_pos) = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos_service(
                str(last_yr_fiscalyear_start_date), str(last_yr_date_to), salesperson_ids, sale_type)

            ly_yr_retail_amount = ly_yr_retail_amount + ly_yr_retail_amount_pos
            ly_yr_invoice_amount = ly_yr_invoice_amount + ly_yr_invoice_amount_pos

            ly_yr_gross_amount = ly_yr_gross_amount + ly_yr_gross_amount_pos

            yr_invoice_inc_dec = ly_yr_invoice_amount and (
                    yr_invoice_amount - ly_yr_invoice_amount) / ly_yr_invoice_amount or 0

            # lly_yr_retail_amount, lly_yr_invoice_amount, lly_yr_gross_amount = self.get_sale_amount(
            #     str(llyr_date_from), str(llyr_date_to), salesperson_ids, sale_type)
            (lly_yr_retail_amount_pos, lly_yr_invoice_amount_pos,
             lly_yr_gross_amount_pos) = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos_service(str(llyr_date_from), str(llyr_date_to),
                                                                            salesperson_ids, sale_type)

            lly_yr_invoice_amount = lly_yr_invoice_amount + lly_yr_invoice_amount_pos
            llyr_invoice_inc_dec = lly_yr_invoice_amount and (
                    ly_yr_invoice_amount - lly_yr_invoice_amount) / lly_yr_invoice_amount or 0

            lly_yr_gross_amount = lly_yr_gross_amount + lly_yr_gross_amount_pos

            invoice_sale = [row_name + ' Sold', 'amount']
            invoice_sale.append(mnth_invoice_amount)
            invoice_sale.append(mnth_invoice_amount - mnth_invoice_plan)
            invoice_sale.append(str(round(mnth_invoice_perc * 100, 2)) + '%')
            invoice_sale.append(ly_mnth_invoice_amount)
            invoice_sale.append(str(round(mnth_invoice_inc_dec * 100, 2)) + '%')
            invoice_sale.append(yr_invoice_amount)
            invoice_sale.append(yr_invoice_plan)
            invoice_sale.append(str(round(yr_invoice_perc * 100, 2)) + '%')
            invoice_sale.append(ly_yr_invoice_amount)
            invoice_sale.append(str(round(yr_invoice_inc_dec * 100, 2)) + '%')
            invoice_sale.append(lly_yr_invoice_amount)
            invoice_sale.append(str(round(llyr_invoice_inc_dec * 100, 2)) + '%')

            max_gross_margin_percentage = 0.0
            if sale_type == 'repair':
                if self.env['ir.config_parameter'].sudo().get_param('repair_gross_margin_max_percentage') or '':
                    max_gross_margin_percentage = float(
                        self.env['ir.config_parameter'].sudo().get_param('repair_gross_margin_max_percentage'))
            else:
                if self.env['ir.config_parameter'].sudo().get_param('service_gross_margin_max_percentage') or '':
                    max_gross_margin_percentage = float(
                        self.env['ir.config_parameter'].sudo().get_param('service_gross_margin_max_percentage'))

            gp_mtd = invoice_sale[2] and mnth_gross_amount / invoice_sale[2] or 0
            if max_gross_margin_percentage:
                if round(gp_mtd * 100, 2) > max_gross_margin_percentage:
                    mnth_gross_amount = ((max_gross_margin_percentage / 100) * invoice_sale[2])
                    gp_mtd = max_gross_margin_percentage / 100
            gp_target = invoice_sale[3] and mnth_gross_plan / invoice_sale[3] or 0
            gp_mplan = gp_target and (gp_mtd) / gp_target or 0
            gp_lymtd = invoice_sale[5] and ly_mnth_gross_amount / invoice_sale[5] or 0
            if max_gross_margin_percentage:
                if round(gp_lymtd * 100, 2) > max_gross_margin_percentage:
                    ly_mnth_gross_amount = ((max_gross_margin_percentage / 100) * invoice_sale[5])
                    gp_lymtd = max_gross_margin_percentage / 100
            gp_minc_dec = gp_lymtd and (gp_mtd - gp_lymtd) or 0
            gp_ytd = invoice_sale[7] and yr_gross_amount / invoice_sale[7] or 0
            if max_gross_margin_percentage:
                if round(gp_ytd * 100, 2) > max_gross_margin_percentage:
                    yr_gross_amount = ((max_gross_margin_percentage / 100) * invoice_sale[7])
                    gp_ytd = max_gross_margin_percentage / 100
            gp_ytarget = invoice_sale[8] and yr_gross_plan / invoice_sale[8] or 0
            gp_yplan = gp_target and (gp_ytd) / gp_target or 0
            gp_lytd = invoice_sale[10] and ly_yr_gross_amount / invoice_sale[10] or 0
            if max_gross_margin_percentage:
                if round(gp_lytd * 100, 2) > max_gross_margin_percentage:
                    ly_yr_gross_amount = ((max_gross_margin_percentage / 100) * invoice_sale[10])
                    gp_lytd = max_gross_margin_percentage / 100
            gp_yinc_dec = gp_lytd and (gp_ytd - gp_lytd) or 0
            gp_llytd = invoice_sale[12] and lly_yr_gross_amount / invoice_sale[12] or 0
            if max_gross_margin_percentage:
                if round(gp_llytd * 100, 2) > max_gross_margin_percentage:
                    lly_yr_gross_amount = ((max_gross_margin_percentage / 100) * invoice_sale[12])
                    gp_llytd = max_gross_margin_percentage / 100
            gp_llyinc_dec = gp_llytd and (gp_lytd - gp_llytd) or 0

            gross_percentage = ['Gross Margin %', 'perc']
            gross_percentage.append(str(round(gp_mtd * 100, 2)) + '%')
            gross_percentage.append('')
            gross_percentage.append(str(round(gp_mplan * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_lymtd * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_minc_dec * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_ytd * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_ytarget * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_yplan * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_lytd * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_yinc_dec * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_llytd * 100, 2)) + '%')
            gross_percentage.append(str(round(gp_llyinc_dec * 100, 2)) + '%')

            mnth_gross_perc = mnth_gross_plan and (mnth_gross_amount) / mnth_gross_plan or 0
            mnth_gross_inc_dec = ly_mnth_gross_amount and (
                    mnth_gross_amount - ly_mnth_gross_amount) / ly_mnth_gross_amount or 0
            yr_gross_perc = yr_gross_plan and (yr_gross_amount) / yr_gross_plan or 0
            yr_gross_inc_dec = ly_yr_gross_amount and (
                    yr_gross_amount - ly_yr_gross_amount) / ly_yr_gross_amount or 0
            llyr_gross_inc_dec = lly_yr_gross_amount and (
                    ly_yr_gross_amount - lly_yr_gross_amount) / lly_yr_gross_amount or 0

            gross_margin = ['Gross Margin $', 'amount']
            gross_margin.append(round(mnth_gross_amount, 2))
            gross_margin.append(mnth_gross_plan)
            gross_margin.append(str(round(mnth_gross_perc * 100, 2)) + '%')
            gross_margin.append(round(ly_mnth_gross_amount, 2))
            gross_margin.append(str(round(mnth_gross_inc_dec * 100, 2)) + '%')
            gross_margin.append(round(yr_gross_amount, 2))
            gross_margin.append(round(yr_gross_plan, 2))
            gross_margin.append(str(round(yr_gross_perc * 100, 2)) + '%')
            gross_margin.append(round(ly_yr_gross_amount, 2))
            gross_margin.append(str(round(yr_gross_inc_dec * 100, 2)) + '%')
            gross_margin.append(round(lly_yr_gross_amount, 2))
            gross_margin.append(str(round(llyr_gross_inc_dec * 100, 2)) + '%')

            line_list.append(invoice_sale)
            line_list.append(gross_margin)
            line_list.append(gross_percentage)
        return line_list

    def get_net_sales(self, total_sale, sales_return, discount, month_start_date, date_to, last_yr_month_start_date,
                      last_yr_date_to, fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                      llyr_date_from, salesperson_ids):

        ns_mtd_all = total_sale[2] + sales_return[2] - discount[2]
        ns_target = self.get_planned_values('sold_amount', month_start_date, date_to, salesperson_ids)
        ns_mplan = ns_target and (ns_mtd_all) / ns_target or 0.00
        ns_lymtd = total_sale[5] + sales_return[5] - discount[5]
        ns_minc_dec = ns_lymtd and (ns_mtd_all - ns_lymtd or 0.00) / ns_lymtd or 0.00

        ns_ytd_all = total_sale[7] + sales_return[7] - discount[7]

        ns_ytarget = self.get_planned_values('sold_amount', last_yr_month_start_date, last_yr_date_to, salesperson_ids)
        ns_yplan = ns_ytarget and (ns_ytd_all) / ns_ytarget or 0.00
        ns_lytd = total_sale[10] + sales_return[10] - discount[10]
        ns_yinc_dec = ns_lytd and (ns_ytd_all - ns_lytd) / ns_lytd or 0.00

        ns_llytd_all = total_sale[12] + sales_return[12] - discount[12]
        # ns_llyplan = ns_llytarget and (ns_llytd) / ns_llytarget or 0
        ns_lyinc_dec = ns_llytd_all and (ns_lytd - ns_llytd_all) / ns_llytd_all or 0.00

        net_sales = ['Net Sale', 'amount']
        net_sales.append(ns_mtd_all)
        net_sales.append(ns_target)
        net_sales.append(str(round(ns_mplan * 100, 2)) + '%')
        net_sales.append(ns_lymtd)
        net_sales.append(str(round(ns_minc_dec * 100, 2)) + '%')
        net_sales.append(ns_ytd_all)
        net_sales.append(ns_ytarget)
        net_sales.append(str(round(ns_yplan * 100, 2)) + '%')
        net_sales.append(ns_lytd)
        net_sales.append(str(round(ns_yinc_dec * 100, 2)) + '%')
        net_sales.append(ns_llytd_all)
        net_sales.append(str(round(ns_lyinc_dec * 100, 2)) + '%')

        return net_sales

    def get_gross_percentage(self, gross_amount, net_invoice, month_start_date, fiscalyear_start_date, date_to,
                             salesperson_ids, llyr_date_from, llyr_date_to):

        gp_mtd = net_invoice[2] and gross_amount[2] / net_invoice[2] or 0
        gp_target, count = self.get_planned_values('gross_percentage', month_start_date, date_to, salesperson_ids,
                                                   get_count=True)

        if count:
            gm = gp_target / count
        else:
            gm = gp_target
        gp_mplan = (gp_target and (gp_mtd) / gp_target or 0) * 100

        gp_lymtd = net_invoice[5] and gross_amount[5] / net_invoice[5] or 0
        gp_minc_dec = gp_lymtd and (gp_mtd - gp_lymtd) or 0
        gp_ytd = net_invoice[7] and gross_amount[7] / net_invoice[7] or 0
        gp_ytarget, count = self.get_planned_values('gross_percentage', fiscalyear_start_date, date_to,
                                                    salesperson_ids,
                                                    get_count=True)

        gp_llytd = net_invoice[12] and gross_amount[12] / net_invoice[12] or 0
        gp_llytarget, count_lly = self.get_planned_values('gross_percentage', llyr_date_from, llyr_date_to,
                                                          salesperson_ids, get_count=True)

        if count:
            gm2 = gp_ytarget / count
        else:
            gm2 = gp_ytarget

        if count_lly:
            gm3 = gp_llytarget / count_lly
        else:
            gm3 = gp_llytarget

        gp_yplan = gp_target and (gp_ytd) / gp_target or 0
        gp_lytd = net_invoice[10] and gross_amount[10] / net_invoice[10] or 0
        gp_yinc_dec = gp_lytd and (gp_ytd - gp_lytd) or 0
        gp_lyinc_dec = gp_llytd and (gp_lytd - gp_llytd) or 0

        gross_percentage = ['Gross Margin %', 'perc']
        gross_percentage.append(str(round(gp_mtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_target, 2)) + '%')
        gross_percentage.append(str(round(gp_mtd * 100, 2) - round(gm, 2)) + '%')
        gross_percentage.append(str(round(gp_lymtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_minc_dec * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_ytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gm2, 2)) + '%')
        gross_percentage.append(str(round(gp_ytd * 100, 2) - round(gm2, 2)) + '%')
        gross_percentage.append(str(round(gp_lytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_yinc_dec * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_llytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_lyinc_dec * 100, 2)) + '%')

        return gross_percentage

    def get_repair_gross_percentage(self, gross_amount, net_invoice, month_start_date, fiscalyear_start_date,
                                    date_to, salesperson_ids, llyr_date_to, llyr_date_from):

        gp_mtd = net_invoice[2] and gross_amount[2] / net_invoice[2] or 0
        gp_target, count = self.get_planned_values(
            'gross_percentage', month_start_date, date_to, salesperson_ids, get_count=True)

        if count:
            gm = gp_target / count
        else:
            gm = gp_target
        gp_mplan = (gp_target and (gp_mtd) / gp_target or 0) * 100

        gp_lymtd = net_invoice[6] and gross_amount[6] / net_invoice[6] or 0
        gp_minc_dec = gp_lymtd and (gp_mtd - gp_lymtd) or 0
        gp_ytd = net_invoice[8] and gross_amount[8] / net_invoice[8] or 0
        gp_ytarget, count = self.get_planned_values(
            'gross_percentage', fiscalyear_start_date, date_to, salesperson_ids, get_count=True)
        if count:
            gm2 = gp_ytarget / count
        else:
            gm2 = gp_ytarget

        gp_llytd = net_invoice[13] and gross_amount[13] / net_invoice[13] or 0
        gp_llytarget, count_lly = self.get_planned_values(
            'gross_percentage', llyr_date_from, llyr_date_to, salesperson_ids, get_count=True)
        if count_lly:
            gm3 = gp_llytarget / count_lly
        else:
            gm3 = gp_llytarget
        gp_yplan = gp_target and (gp_ytd) / gp_target or 0
        gp_lytd = net_invoice[11] and gross_amount[11] / net_invoice[11] or 0
        gp_yinc_dec = gp_lytd and (gp_ytd - gp_lytd) or 0

        gross_percentage = ['Gross Margin %', 'perc']
        gross_percentage.append(str(round(gp_mtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gm, 2)) + '%')
        gross_percentage.append(str(round(gp_mtd * 100, 2) - round(gm, 2)) + '%')
        gross_percentage.append('')
        gross_percentage.append(str(round(gp_lymtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_minc_dec * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_ytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gm2, 2)) + '%')
        gross_percentage.append(str(round(gp_ytd * 100, 2) - round(gm2, 2)) + '%')
        gross_percentage.append(str(round(gp_lytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_yinc_dec * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_llytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gm3, 2)) + '%')
        gross_percentage.append(str(round(gp_llytd * 100, 2) - round(gm3, 2)) + '%')

        return gross_percentage

    def get_sale_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                       fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from):
        user_ids = self.env['res.users']
        context = self.env.context
        # import pdb;pdb.set_trace()
        if 'options' in context:
            salesperson_ids = self.env['res.users'].browse(context['options']['users_ids'])
            user_ids|=salesperson_ids
        else:
            salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        sales_list = []

        if salesperson_ids:
            state_domain = [('state', 'in', ['sale', 'done']), ('order_id.user_id', 'in', salesperson_ids), ]
            sale_type_domain = [('product_id.categ_id.sale_type', '=', 'sale'),
                                ('product_id.exclude_from_report', '=', False)]
            domain = state_domain + sale_type_domain

            retail_sale = ['Gross Sales', 'amount']
            discount = ['Discount $', 'amount']
            discount_per = ['Discount %', 'perc']
            sales = ['Sales', 'amount']
            invoice_sales = ['Total Sold', 'amount']
            returned_sale = ['Returned', 'amount']
            returned_sales = ['Returned', 'amount']
            gross_margin = ['Gross Margin $', 'amount']
            (mnth_retail_amount, mnth_invoice_amount,
             mnth_gross_amount,ly_mnth_retail_amount, ly_mnth_invoice_amount, ly_mnth_gross_amount,
             yr_retail_amount, yr_invoice_amount, yr_gross_amount,
             ly_yr_retail_amount, ly_yr_invoice_amount, ly_yr_gross_amount,
             lly_yr_retail_amount, lly_yr_invoice_amount, lly_yr_gross_amount
             ) = self.with_context({'user_ids':user_ids}).get_sale_amount(
                str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),str(llyr_date_from), str(llyr_date_to), salesperson_ids, check_delivery=True)

            (mnth_retail_amount_pos, mnth_invoice_amount_pos,
             mnth_gross_amount_pos) = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos(
                str(month_start_date), date_to, salesperson_ids, sale_type='sale', check_delivery=True)

            mnth_retail_amount = mnth_retail_amount + mnth_retail_amount_pos
            mnth_invoice_amount = mnth_invoice_amount + mnth_invoice_amount_pos
            mnth_gross_amount = mnth_gross_amount + mnth_gross_amount_pos

            (mnth_so_return_amount, mnth_so_return_cost,
             mnth_so_return_gross_amount,ly_mnth_so_return_amount, ly_mnth_so_return_cost, 
             ly_so_return_gross_amount,yr_so_return_amount, yr_so_return_cost, 
             yr_so_return_gross_amount,ly_yr_so_return_amount, ly_yr_so_return_cost
             , ly_yr_so_return_gross_amount, lly_yr_so_return_amount, lly_yr_so_return_cost
             , lly_yr_so_return_gross_amount) =self.with_context({'user_ids':user_ids}).get_so_return_amount(salesperson_ids,str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),str(llyr_date_from), str(llyr_date_to))

            (mnth_so_return_amount_pos, mnth_so_return_cost_pos,
             mnth_so_return_gross_amount_pos,ly_mnth_so_return_amount_pos, ly_mnth_so_return_cost_pos
             , ly_so_return_gross_amount_pos, yr_so_return_amount_pos
             , yr_so_return_cost_pos, yr_so_return_gross_amount_pos
             ,ly_yr_so_return_amount_pos, ly_yr_so_return_cost_pos, ly_yr_so_return_gross_amount_pos,
             lly_yr_so_return_amount_pos,lly_yr_so_return_cost_pos,lly_yr_so_return_gross_amount_pos) = self.with_context({'user_ids':user_ids}).get_so_return_amount_of_pos(salesperson_ids, str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),str(llyr_date_from), str(llyr_date_to))

            mnth_so_return_amount = mnth_so_return_amount + mnth_so_return_amount_pos
            mnth_so_return_cost = mnth_so_return_cost + mnth_so_return_cost_pos
            mnth_discount_amount = mnth_retail_amount - mnth_invoice_amount

            mnth_gross_amount = mnth_gross_amount - (mnth_so_return_gross_amount + mnth_so_return_gross_amount_pos)
            #
            mnth_retail_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                       salesperson_ids)

            mnth_gross_plan = self.get_planned_values('sale' + '_gross_amount', month_start_date, date_to,
                                                      salesperson_ids)
            mnth_so_return_plan = -abs(self.get_planned_values(
                'return_amount', month_start_date, date_to, salesperson_ids))

            mnth_retail_perc = mnth_retail_plan and (mnth_retail_amount) / mnth_retail_plan or 0

            mnth_gross_perc = 0

            mnth_so_return_perc = mnth_so_return_plan and (mnth_so_return_amount) / mnth_so_return_plan or 0

            ly_mnth_retail_amount_pos, ly_mnth_invoice_amount_pos, ly_mnth_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos(
                str(last_yr_month_start_date), str(last_yr_date_to), salesperson_ids, check_delivery=True)
            ly_mnth_retail_amount = ly_mnth_retail_amount + ly_mnth_retail_amount_pos
            ly_mnth_invoice_amount = ly_mnth_invoice_amount + ly_mnth_invoice_amount_pos
            ly_mnth_gross_amount = ly_mnth_gross_amount + ly_mnth_gross_amount_pos

            ly_mnth_so_return_amount = ly_mnth_so_return_amount + ly_mnth_so_return_amount_pos
            ly_mnth_so_return_cost = ly_mnth_so_return_cost + ly_mnth_so_return_cost_pos
            ly_mnth_discount_amount = ly_mnth_retail_amount - ly_mnth_invoice_amount
            ly_mnth_gross_amount = ly_mnth_gross_amount - (ly_so_return_gross_amount + ly_so_return_gross_amount_pos)

            mnth_retail_inc_dec = ly_mnth_retail_amount and (
                    mnth_retail_amount - ly_mnth_retail_amount) / ly_mnth_retail_amount or 0.00

            mnth_so_return_inc_dec = ly_mnth_so_return_amount and (
                    mnth_so_return_amount - ly_mnth_so_return_amount) / ly_mnth_so_return_amount or 0.00

          
            yr_retail_amount_pos, yr_invoice_amount_pos, yr_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos(
                str(fiscalyear_start_date), date_to, salesperson_ids, check_delivery=True)
            yr_retail_amount = yr_retail_amount + yr_retail_amount_pos
            yr_invoice_amount = yr_invoice_amount + yr_invoice_amount_pos
            yr_gross_amount = yr_gross_amount + yr_gross_amount_pos

            yr_so_return_amount = yr_so_return_amount + yr_so_return_amount_pos
            yr_so_return_cost = yr_so_return_cost + yr_so_return_cost_pos
            yr_discount_amount = yr_retail_amount - yr_invoice_amount
            yr_gross_amount = yr_gross_amount - (yr_so_return_gross_amount + yr_so_return_gross_amount_pos)
            #
            yr_retail_plan = self.with_context({'user_ids':user_ids}).get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                     salesperson_ids)
            yr_gross_plan = 0
            yr_so_return_plan = -abs(
                self.with_context({'user_ids':user_ids}).get_planned_values('return_amount', fiscalyear_start_date, date_to, salesperson_ids))
            yr_retail_perc = yr_retail_plan and (yr_retail_amount) / yr_retail_plan or 0
            yr_gross_perc = 0
            yr_so_return_perc = yr_so_return_plan and (yr_so_return_amount) / yr_so_return_plan or 0

          
            ly_yr_retail_amount_pos, ly_yr_invoice_amount_pos, ly_yr_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos(
                str(last_yr_fiscalyear_start_date), str(last_yr_date_to), salesperson_ids, check_delivery=True)
            ly_yr_retail_amount = ly_yr_retail_amount + ly_yr_retail_amount_pos
            ly_yr_invoice_amount = ly_yr_invoice_amount + ly_yr_invoice_amount_pos
            ly_yr_gross_amount = ly_yr_gross_amount + ly_yr_gross_amount_pos

            ly_yr_so_return_amount = ly_yr_so_return_amount + ly_yr_so_return_amount_pos
            ly_yr_so_return_cost = ly_yr_so_return_cost + ly_yr_so_return_cost_pos
            ly_yr_discount_amount = ly_yr_retail_amount - ly_yr_invoice_amount
            ly_yr_gross_amount = ly_yr_gross_amount - (ly_yr_so_return_gross_amount + ly_yr_so_return_gross_amount_pos)

            lly_yr_so_return_amount = lly_yr_so_return_amount + lly_yr_so_return_amount_pos
            lly_yr_so_return_cost = lly_yr_so_return_cost + lly_yr_so_return_cost_pos
            yr_retail_inc_dec = ly_yr_retail_amount and (
                    yr_retail_amount - ly_yr_retail_amount) / ly_yr_retail_amount or 0
            yr_so_return_inc_dec = ly_yr_so_return_amount and (
                    yr_so_return_amount - ly_yr_so_return_amount) / ly_yr_so_return_amount or 0

            lly_yr_retail_amount_pos, lly_yr_invoice_amount_pos, lly_yr_gross_amount_pos = self.with_context({'user_ids':user_ids}).get_sale_amount_of_pos(
                str(llyr_date_from), str(llyr_date_to), salesperson_ids, check_delivery=True)

            lly_yr_retail_amount = lly_yr_retail_amount + lly_yr_retail_amount_pos
            lly_yr_invoice_amount = lly_yr_invoice_amount + lly_yr_invoice_amount_pos
            lly_yr_gross_amount = lly_yr_gross_amount + lly_yr_gross_amount_pos

            lly_yr_discount_amount = lly_yr_retail_amount - lly_yr_invoice_amount
            lly_yr_gross_amount = lly_yr_gross_amount - (
                    lly_yr_so_return_gross_amount + lly_yr_so_return_gross_amount_pos)
            llyr_so_return_plan = -abs(
                self.with_context({'user_ids':user_ids}).get_planned_values('return_amount', llyr_date_from, llyr_date_to, salesperson_ids))
            #
            llyr_so_return_perc = llyr_so_return_plan and (lly_yr_so_return_amount) / llyr_so_return_plan or 0
            llyr_retail_inc_dec = lly_yr_retail_amount and (
                    ly_yr_retail_amount - lly_yr_retail_amount) / lly_yr_retail_amount or 0

            llyr_so_return_inc_dec = lly_yr_so_return_amount and (
                    ly_yr_so_return_amount - lly_yr_so_return_amount) / lly_yr_so_return_amount or 0

            retail_sale.append(mnth_retail_amount or 0.00)
            retail_sale.append('' or '0.00')
            retail_sale.append(str(round(mnth_retail_perc * 100, 2) or 0.00) + '%' or '0.00')
            retail_sale.append(ly_mnth_retail_amount or 0.00)
            retail_sale.append(str(round(mnth_retail_inc_dec * 100, 2)) + '%' or '0.00')
            retail_sale.append(yr_retail_amount or 0.00)
            retail_sale.append('' or '0.00')
            retail_sale.append(str(round(yr_retail_perc * 100, 2)) + '%' or '0.00')
            retail_sale.append(ly_yr_retail_amount or 0.00)
            retail_sale.append(str(round(yr_retail_inc_dec * 100, 2)) + '%' or '0.00')
            retail_sale.append(lly_yr_retail_amount or 0.00)
            retail_sale.append(str(round(llyr_retail_inc_dec * 100, 2)) + '%' or '0.00')

            mnth_discount_per = mnth_retail_amount and mnth_discount_amount / mnth_retail_amount
            ly_discount_per = ly_mnth_retail_amount and ly_mnth_discount_amount / ly_mnth_retail_amount
            yr_discount_per = yr_retail_amount and yr_discount_amount / yr_retail_amount
            ly_yr_discount_per = ly_yr_retail_amount and ly_yr_discount_amount / ly_yr_retail_amount
            lly_yr_discount_per = lly_yr_retail_amount and lly_yr_discount_amount / lly_yr_retail_amount

            # discount.append(mnth_disc_amount)
            discount.append(mnth_discount_amount)
            discount.append('')
            discount.append('0.00')
            # discount.append(ly_mnth_disc_amount)
            discount.append(ly_mnth_discount_amount)
            discount.append('0.00')
            discount.append(yr_discount_amount)
            # discount.append(yr_disc_amount)
            discount.append('0.00')
            discount.append('0.00')
            # discount.append(ly_yr_disc_amount)
            discount.append(ly_yr_discount_amount)
            discount.append('0.00')
            # discount.append(lly_mnth_disc_amount)
            discount.append(lly_yr_discount_amount)
            discount.append('0.00')

            # discount_per.append(str(round(mnth_disc_per * 100, 2)) + '%')
            discount_per.append(str(round(mnth_discount_per * 100, 2)) + '%')
            discount_per.append('')
            discount_per.append('0.00')
            discount_per.append(str(round(ly_discount_per * 100, 2)) + '%')
            # discount_per.append(str(round(ly_disc_per * 100, 2)) + '%')
            discount_per.append('0.00')
            # discount_per.append(str(round(yr_disc_per * 100, 2)) + '%')
            discount_per.append(str(round(yr_discount_per * 100, 2)) + '%')
            discount_per.append('0.00')
            discount_per.append('0.00')
            discount_per.append(str(round(ly_yr_discount_per * 100, 2)) + '%')
            # discount_per.append(str(round(ly_yr_disc_per * 100, 2)) + '%')
            discount_per.append('0.00')
            # discount_per.append(str(round(lly_yr_disc_per * 100, 2)) + '%')
            discount_per.append(str(round(lly_yr_discount_per * 100, 2)) + '%')
            discount_per.append('0.00')

            returned_sale.append(mnth_so_return_amount)
            returned_sale.append('')
            returned_sale.append(str(round(mnth_so_return_perc * 100, 2)) + '%')
            returned_sale.append(ly_mnth_so_return_amount)
            returned_sale.append(str(round(mnth_so_return_inc_dec * 100, 2)) + '%')
            returned_sale.append(yr_so_return_amount)
            returned_sale.append('0.00')
            returned_sale.append(str(round(yr_so_return_perc * 100, 2)) + '%')
            returned_sale.append(ly_yr_so_return_amount)
            returned_sale.append(str(round(yr_so_return_inc_dec * 100, 2)) + '%')
            returned_sale.append(lly_yr_so_return_amount)
            returned_sale.append(str(round(llyr_so_return_inc_dec * 100, 2)) + '%')
            mnth_sale_inc_dec = (ly_mnth_retail_amount + ly_mnth_so_return_amount) and (
                    (mnth_retail_amount + mnth_so_return_amount) - (
                    ly_mnth_retail_amount + ly_mnth_so_return_amount)) / (
                                        ly_mnth_retail_amount + ly_mnth_so_return_amount) or 0
            yr_sale_inc_dec = (ly_yr_retail_amount + ly_yr_so_return_amount) and (
                    (yr_retail_amount + yr_so_return_amount) - (ly_yr_retail_amount + ly_yr_so_return_amount)) / (
                                      ly_yr_retail_amount + ly_yr_so_return_amount) or 0
            lly_yr_sale_inc_dec = (lly_yr_retail_amount + lly_yr_so_return_amount) and (
                    (ly_yr_retail_amount + ly_yr_so_return_amount) - (
                    lly_yr_retail_amount + lly_yr_so_return_amount)) / (
                                          lly_yr_retail_amount + lly_yr_so_return_amount) or 0
            sales.append(mnth_retail_amount + mnth_so_return_amount)
            sales.append('')
            sales.append('0.00')
            sales.append(ly_mnth_retail_amount + ly_mnth_so_return_amount)
            sales.append(str(round(mnth_sale_inc_dec * 100, 2)) + '%')
            sales.append(yr_retail_amount + yr_so_return_amount)
            sales.append('0.00')
            sales.append('0.00')
            sales.append(ly_yr_retail_amount + ly_yr_so_return_amount)
            sales.append(str(round(yr_sale_inc_dec * 100, 2)) + '%')
            sales.append(lly_yr_retail_amount + lly_yr_so_return_amount)
            sales.append(str(round(lly_yr_sale_inc_dec * 100, 2)) + '%')

            sales_list.append(retail_sale)
            sales_list.append(returned_sale)
            sales_list.append(sales)
            sales_list.append(discount)
            sales_list.append(discount_per)

            net_sale = self.get_net_sales(retail_sale, returned_sale, discount, month_start_date, date_to,
                                          last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                          last_yr_fiscalyear_start_date, llyr_date_to,
                                          llyr_date_from, salesperson_ids)
            #
            sales_list.append(net_sale)
            if self.env['ir.config_parameter'].sudo().get_param('additional_cogs_percentage') or '':
                additional_cogs_percentage = float(
                    self.env['ir.config_parameter'].sudo().get_param('additional_cogs_percentage'))
                if additional_cogs_percentage:
                    mnth_gross_amount = mnth_gross_amount - ((additional_cogs_percentage / 100) * net_sale[2])
                    ly_mnth_gross_amount = ly_mnth_gross_amount - ((additional_cogs_percentage / 100) * net_sale[5])
                    yr_gross_amount = yr_gross_amount - ((additional_cogs_percentage / 100) * net_sale[7])
                    ly_yr_gross_amount = ly_yr_gross_amount - ((additional_cogs_percentage / 100) * net_sale[10])
                    lly_yr_gross_amount = lly_yr_gross_amount - ((additional_cogs_percentage / 100) * net_sale[12])
            mnth_gross_inc_dec = ly_mnth_gross_amount and (
                    mnth_gross_amount - ly_mnth_gross_amount) / ly_mnth_gross_amount or 0
            yr_gross_inc_dec = ly_yr_gross_amount and (
                    yr_gross_amount - ly_yr_gross_amount) / ly_yr_gross_amount or 0
            llyr_gross_inc_dec = lly_yr_gross_amount and (
                    ly_yr_gross_amount - lly_yr_gross_amount) / lly_yr_gross_amount or 0
            gross_margin.append(round(mnth_gross_amount, 2))
            gross_margin.append(mnth_gross_plan)
            gross_margin.append(str(round(mnth_gross_perc * 100, 2)) + '%')
            gross_margin.append(round(ly_mnth_gross_amount, 2))
            gross_margin.append(str(round(mnth_gross_inc_dec * 100, 2)) + '%')
            gross_margin.append(round(yr_gross_amount, 2))
            gross_margin.append(round(yr_gross_plan, 2))
            gross_margin.append(str(round(yr_gross_perc * 100, 2)) + '%')
            gross_margin.append(round(ly_yr_gross_amount, 2))
            gross_margin.append(str(round(yr_gross_inc_dec * 100, 2)) + '%')
            gross_margin.append(lly_yr_gross_amount)
            gross_margin.append(str(round(llyr_gross_inc_dec * 100, 2)) + '%')
            sales_list.append(gross_margin)
            #
            gross_percentage = self.get_gross_percentage(gross_margin, net_sale, month_start_date,
                                                         fiscalyear_start_date, date_to, salesperson_ids,
                                                         llyr_date_from, llyr_date_to)
            #
            sales_list.append(gross_percentage)
        return sales_list

    def get_sale_count(self, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date,llyr_date_from,llyr_date_to, salesperson_ids, sale_type='sale'):
        if date_from:
            date_from += ' 00:00:00'
        if last_yr_month_start_date:
            last_yr_month_start_date+= ' 00:00:00'
        if last_yr_date_to:
            last_yr_date_to += ' 23:59:59'
        if fiscalyear_start_date:
            fiscalyear_start_date+= ' 00:00:00'
        if last_yr_fiscalyear_start_date:
            last_yr_fiscalyear_start_date+= ' 00:00:00'
        if llyr_date_from:
            llyr_date_from+= ' 00:00:00'
        if llyr_date_to:
            llyr_date_to+= ' 23:59:59'
        if date_to:
            date_to += ' 23:59:59'
        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)
        llyr_date_from = self.get_date_with_tz(llyr_date_from)
        llyr_date_to = self.get_date_with_tz(llyr_date_to)

        ids = ''

        context = self.env.context
        user_ids = self.env['res.users'].browse(context.get('users_ids', []))
        salesperson = salesperson_ids
        if salesperson and not user_ids:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'
        else:
            salesperson_str = ','.join(str(x) for x in user_ids.ids)
            ids = '(' + salesperson_str + ')'
        if ids:
            sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as net_qty
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as sale_count                    
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id and so.user_id in %s
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as ly_m_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as ly_m_sale_count                    
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id and so.user_id in %s
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as y_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as y_sale_count                    
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id and so.user_id in %s
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as ly_y_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id and so.user_id in %s
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as lly_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as lly_sale_count 
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
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id and so.user_id in %s
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                """) % (date_from, date_to,ids,last_yr_month_start_date,last_yr_date_to,ids,fiscalyear_start_date,date_to,ids,last_yr_fiscalyear_start_date,last_yr_date_to,ids,llyr_date_from,llyr_date_to,ids)

        else:
            sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as net_qty
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                     0.0 as net_qty
                    ,0.0 as sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as ly_m_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                     0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as y_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                     0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as ly_y_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as ly_y_sale_count
                    ,0.0 as lly_item_count
                    ,0.0 as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                     0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count
                    ,0.0 as ly_m_sale_count
                    ,0.0 as y_item_count
                    ,0.0 as y_sale_count
                    ,0.0 as ly_y_item_count
                    ,0.0 as ly_y_sale_count 
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as lly_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as lly_sale_count
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
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                """) %(date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        sale_count = 0
        product_count = 0
        ly_m_sale_count=0
        ly_m_item_count=0
        y_sale_count=0
        y_item_count=0
        ly_y_sale_count=0
        ly_y_item_count=0
        lly_sale_count=0
        lly_item_count = 0
        for value in res:
            product_count += value.get('net_qty', 0) or 0
            sale_count += value.get('sale_count', 0) or 0
            ly_m_item_count += value.get('ly_m_item_count', 0) or 0
            ly_m_sale_count += value.get('ly_m_sale_count', 0) or 0
            y_item_count += value.get('y_item_count', 0) or 0
            y_sale_count += value.get('y_sale_count', 0) or 0
            ly_y_item_count += value.get('ly_y_item_count', 0) or 0
            ly_y_sale_count += value.get('ly_y_sale_count', 0) or 0
            lly_item_count += value.get('lly_item_count', 0) or 0
            lly_sale_count += value.get('lly_sale_count', 0) or 0

        if ids:
            other_sql = ("""
                    select 
                        SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as net_qty
                        ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as sale_count
                        ,0.0 as ly_m_item_count
                        ,0.0 as ly_m_sale_count
                        ,0.0 as y_item_count
                        ,0.0 as y_sale_count
                        ,0.0 as ly_y_item_count
                        ,0.0 as ly_y_sale_count 
                        ,0.0 as lly_item_count 
                        ,0.0 as lly_sale_count
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code in ('outgoing', 'incoming')
                        and sm.state='done' 
                        and sm.product_id = sol.product_id 
                        and other.res_users_id in %s
                        and pt.exclude_from_report !=True 
                    GROUP BY so.id
                    UNION ALL
                    select
                          0.0 as net_qty
                        , 0.0 as sale_count
                        ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as ly_m_item_count
                        ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as ly_m_sale_count
                        ,0.0 as y_item_count
                        ,0.0 as y_sale_count
                        ,0.0 as ly_y_item_count
                        ,0.0 as ly_y_sale_count 
                        ,0.0 as lly_item_count 
                        ,0.0 as lly_sale_count
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code in ('outgoing', 'incoming')
                        and sm.state='done' 
                        and sm.product_id = sol.product_id 
                        and other.res_users_id in %s
                        and pt.exclude_from_report !=True 
                    GROUP BY so.id
                    UNION ALL
                    select
                          0.0 as net_qty
                        , 0.0 as sale_count
                        ,0.0 as ly_m_item_count
                        ,0.0 as ly_m_sale_count
                        ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as y_item_count
                        ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as y_sale_count
                        ,0.0 as ly_y_item_count
                        ,0.0 as ly_y_sale_count 
                        ,0.0 as lly_item_count 
                        ,0.0 as lly_sale_count
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code in ('outgoing', 'incoming')
                        and sm.state='done' 
                        and sm.product_id = sol.product_id 
                        and other.res_users_id in %s
                        and pt.exclude_from_report !=True 
                    GROUP BY so.id
                    UNION ALL
                    select
                          0.0 as net_qty
                        , 0.0 as sale_count
                        ,0.0 as ly_m_item_count
                        ,0.0 as ly_m_sale_count
                        ,0.0 as y_item_count
                        ,0.0 as y_sale_count
                        ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as ly_y_item_count
                        ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as ly_y_sale_count
                        ,0.0 as lly_item_count 
                        ,0.0 as lly_sale_count
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code in ('outgoing', 'incoming')
                        and sm.state='done' 
                        and sm.product_id = sol.product_id 
                        and other.res_users_id in %s
                        and pt.exclude_from_report !=True 
                    GROUP BY so.id
                    UNION ALL
                    select
                          0.0 as net_qty
                        , 0.0 as sale_count
                        ,0.0 as ly_m_item_count
                        ,0.0 as ly_m_sale_count
                        ,0.0 as y_item_count
                        ,0.0 as y_sale_count
                        ,0.0 as ly_y_item_count
                        ,0.0 as ly_y_sale_count 
                        ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as lly_item_count
                        ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as lly_sale_count
                    from sale_order_line sol
                        inner join sale_order so on (so.id = sol.order_id)
                        inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                        inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                        inner join stock_move sm on (sp.id = sm.picking_id)
                        inner join res_partner rp on (rp.id = so.partner_id)
                        inner join product_product pp on (sol.product_id = pp.id)
                        inner join product_template pt on (pp.product_tmpl_id = pt.id)
                        inner join product_category pc on (pc.id = pt.categ_id) 
                        inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                    where sp.date_done >= '%s' 
                        and sp.date_done <= '%s' 
                        and sp.state = 'done' 
                        and spt.code in ('outgoing', 'incoming')
                        and sm.state='done' 
                        and sm.product_id = sol.product_id 
                        and other.res_users_id in %s
                        and pt.exclude_from_report !=True 
                    GROUP BY so.id
                    """) % (date_from, date_to,ids,last_yr_month_start_date,last_yr_date_to,ids,fiscalyear_start_date,date_to,ids,last_yr_fiscalyear_start_date,last_yr_date_to,ids,llyr_date_from,llyr_date_to,ids)
        else:
            other_sql = ("""
                select 
                     SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as net_qty
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as sale_count
                    ,0.0 as other_ly_m_item_count
                    , 0.0 as other_ly_m_sale_count
                    , 0.0 as other_y_item_count
                    , 0.0 as other_y_sale_count
                    , 0.0 as other_ly_y_item_count
                    , 0.0 as other_ly_y_sale_count
                    , 0.0 as other_lly_item_count
                    , 0.0 as other_lly_sale_count
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                      0.0 as net_qty
                    , 0.0 as sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as other_ly_m_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as other_ly_m_sale_count
                    , 0.0 as other_y_item_count
                    , 0.0 as other_y_sale_count
                    , 0.0 as other_ly_y_item_count
                    , 0.0 as other_ly_y_sale_count
                    , 0.0 as other_lly_item_count
                    , 0.0 as other_lly_sale_count
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                     0.0 as net_qty
                    , 0.0 as sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as other_ly_m_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as other_ly_m_sale_count
                    , 0.0 as other_y_item_count
                    , 0.0 as other_y_sale_count
                    , 0.0 as other_ly_y_item_count
                    , 0.0 as other_ly_y_sale_count
                    , 0.0 as other_lly_item_count
                    , 0.0 as other_lly_sale_count
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code in ('outgoing', 'incoming')
                    and sm.state='done' 
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                      0.0 as net_qty
                    , 0.0 as sale_count
                    ,0.0 as other_ly_m_item_count
                    , 0.0 as other_ly_m_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as other_y_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as other_y_sale_count
                    , 0.0 as other_ly_y_item_count
                    , 0.0 as other_ly_y_sale_count
                    , 0.0 as other_lly_item_count
                    , 0.0 as other_lly_sale_count
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and sm.state='done' 
                    and spt.code in ('outgoing', 'incoming')
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                      0.0 as net_qty
                    , 0.0 as sale_count
                    ,0.0 as other_ly_m_item_count
                    , 0.0 as other_ly_m_sale_count
                    , 0.0 as other_y_item_count
                    , 0.0 as other_y_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as other_ly_y_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as other_ly_y_sale_count
                    , 0.0 as other_lly_item_count
                    , 0.0 as other_lly_sale_count
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and sm.state='done' 
                    and spt.code in ('outgoing', 'incoming')
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                UNION ALL
                select 
                      0.0 as net_qty
                    , 0.0 as sale_count
                    ,0.0 as other_ly_m_item_count
                    , 0.0 as other_ly_m_sale_count
                    , 0.0 as other_y_item_count
                    , 0.0 as other_y_sale_count
                    , 0.0 as other_ly_y_item_count
                    , 0.0 as other_ly_y_sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) ELSE 0 END) as other_lly_item_count
                    ,round(1.0/(SELECT count(sale_order_id)+1 from res_users_sale_order_rel where (sale_order_id = so.id)), 2) as other_lly_sale_count
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join res_users_sale_order_rel other on (other.sale_order_id = so.id)
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and sm.state='done' 
                    and spt.code in ('outgoing', 'incoming')
                    and sm.product_id = sol.product_id 
                    and pt.exclude_from_report!=True
                GROUP BY so.id
                """) % (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)
        self._cr.execute(other_sql)
        other_res = self._cr.dictfetchall()
        other_sale_count = 0
        other_product_count = 0
        other_ly_m_sale_count=0
        other_ly_m_item_count=0
        other_y_sale_count=0
        other_y_item_count=0
        other_ly_y_sale_count=0
        other_ly_y_item_count=0
        other_lly_sale_count=0
        other_lly_item_count = 0
        for other_value in other_res:
            other_product_count += other_value.get('net_qty', 0) or 0
            other_sale_count += other_value.get('sale_count', 0) or 0
            other_product_count += other_value.get('net_qty', 0) or 0
            other_ly_m_sale_count += other_value.get('other_ly_m_sale_count', 0) or 0
            other_ly_m_item_count += other_value.get('other_ly_m_item_count', 0) or 0
            other_y_sale_count += other_value.get('other_y_sale_count', 0) or 0
            other_y_item_count += other_value.get('other_y_item_count', 0) or 0
            other_ly_y_sale_count += other_value.get('other_ly_y_sale_count', 0) or 0
            other_ly_y_item_count += other_value.get('other_ly_y_item_count', 0) or 0
            other_lly_sale_count += other_value.get('other_lly_sale_count', 0) or 0
            other_lly_item_count += other_value.get('other_lly_item_count', 0) or 0

        return sale_count + other_sale_count, product_count + other_product_count,ly_m_sale_count + other_ly_m_sale_count, ly_m_item_count + other_ly_m_item_count,y_sale_count + other_y_sale_count, y_item_count + other_y_item_count,ly_y_sale_count + other_ly_y_sale_count, ly_y_item_count + other_ly_y_item_count,lly_sale_count + other_lly_sale_count, lly_item_count + other_lly_item_count

    def get_sale_count_of_pos(self, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date,llyr_date_from,llyr_date_to, salesperson_ids, sale_type='sale'):
        if date_from:
            date_from += ' 00:00:00'
        if last_yr_month_start_date:
            last_yr_month_start_date+= ' 00:00:00'
        if last_yr_date_to:
            last_yr_date_to += ' 23:59:59'
        if fiscalyear_start_date:
            fiscalyear_start_date+= ' 00:00:00'
        if last_yr_fiscalyear_start_date:
            last_yr_fiscalyear_start_date+= ' 00:00:00'
        if llyr_date_from:
            llyr_date_from+= ' 00:00:00'
        if llyr_date_to:
            llyr_date_to+= ' 23:59:59'
        if date_to:
            date_to += ' 23:59:59'
        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)
        llyr_date_from = self.get_date_with_tz(llyr_date_from)
        llyr_date_to = self.get_date_with_tz(llyr_date_to)

        ids = ''

        context = self.env.context
        user_ids = self.env['res.users'].browse(context.get('users_ids', []))
        salesperson = salesperson_ids
        if salesperson and not user_ids:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'
        else:
            salesperson_str = ','.join(str(x) for x in user_ids.ids)
            ids = '(' + salesperson_str + ')'

        if ids:
            sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as net_qty
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and sm.state='done'
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pt.exclude_from_report!=True
                GROUP BY po.id
                UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_m_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and sm.state='done'
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pt.exclude_from_report!=True
                GROUP BY po.id
                UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and sm.state='done'
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pt.exclude_from_report!=True
                GROUP BY po.id
                 UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and sm.state='done'
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pt.exclude_from_report!=True
                GROUP BY po.id
                 UNION ALL
                select 
                    0.0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as lly_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s'
                    and sp.state = 'done' 
                    and sm.state='done'
                    and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = pol.product_id
                    and he.user_id in %s 
                    and pt.exclude_from_report!=True
                GROUP BY po.id
                """) %(date_from, date_to,ids,last_yr_month_start_date,last_yr_date_to,ids,fiscalyear_start_date,date_to,ids,last_yr_fiscalyear_start_date,last_yr_date_to,ids,llyr_date_from,llyr_date_to,ids)

        else:
            sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as net_qty
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select
                    0.0 as net_qty
                    ,0.0 as  sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_m_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                 UNION ALL
                select
                    0.0 as net_qty
                    ,0.0 as  sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select
                    0.0 as net_qty
                    ,0.0 as  sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select
                    0.0 as net_qty
                    ,0.0 as  sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as lly_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                    inner join hr_employee he on (he.id = po.employee_id) 
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                """) % (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)

        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        sale_count = 0
        product_count = 0
        ly_m_item_count_pos = 0
        ly_m_sale_count_pos = 0
        y_item_count_pos = 0
        y_sale_count_pos = 0
        ly_y_item_count_pos = 0
        ly_y_sale_count_pos = 0
        lly_item_count_pos = 0
        lly_sale_count_pos = 0
        for value in res:
            product_count += value.get('net_qty', 0) or 0
            sale_count += value.get('sale_count', 0) or 0
            ly_m_item_count_pos += value.get('ly_m_item_count_pos', 0) or 0
            ly_m_sale_count_pos += value.get('ly_m_sale_count_pos', 0) or 0
            y_item_count_pos += value.get('y_item_count_pos', 0) or 0
            y_sale_count_pos += value.get('y_sale_count_pos', 0) or 0
            ly_y_item_count_pos += value.get('ly_y_item_count_pos', 0) or 0
            ly_y_sale_count_pos += value.get('ly_y_sale_count_pos', 0) or 0
            lly_item_count_pos += value.get('lly_item_count_pos', 0) or 0
            lly_sale_count_pos += value.get('lly_sale_count_pos', 0) or 0

        if ids:
            other_sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as net_qty
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
        
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and other.res_users_id  in %s and pt.exclude_from_report!=True
                GROUP BY po.id
                UNION ALL
                select
                    0.0 as net_qty
                    ,0.0 as sale_count 
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_m_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_m_sale_count_pos                   
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
        
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and other.res_users_id  in %s and pt.exclude_from_report!=True
                GROUP BY po.id
                UNION ALL
                select
                     0.0 as net_qty
                    ,0.0 as sale_count 
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
        
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and other.res_users_id  in %s and pt.exclude_from_report!=True
                GROUP BY po.id
                UNION ALL
                select
                     0.0 as net_qty
                    ,0.0 as sale_count 
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
        
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and other.res_users_id  in %s and pt.exclude_from_report!=True
                GROUP BY po.id
                UNION ALL
                select
                     0.0 as net_qty
                    ,0.0 as sale_count 
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as lly_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as lly_sale_count_pos

                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 
        
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and other.res_users_id  in %s and pt.exclude_from_report!=True
                GROUP BY po.id
                """) % (date_from, date_to,ids,last_yr_month_start_date,last_yr_date_to,ids,fiscalyear_start_date,date_to,ids,last_yr_fiscalyear_start_date,last_yr_date_to,ids,llyr_date_from,llyr_date_to,ids)
        else:
            other_sql = ("""
                select 
                    SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as net_qty
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 

                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select 
                    0,0 as net_qty
                    ,0.0 as sale_count
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_m_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 

                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select 
                    0,0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as y_sale_count_pos
                    , 0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 

                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select 
                    0,0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as ly_y_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as ly_y_sale_count_pos
                    , 0.0 as lly_item_count_pos 
                    ,0.0 as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 

                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                UNION ALL
                select 
                    0,0 as net_qty
                    ,0.0 as sale_count
                    ,0.0 as ly_m_item_count_pos
                    ,0.0 as ly_m_sale_count_pos
                    , 0.0 as y_item_count_pos
                    , 0.0 as y_sale_count_pos
                     ,0.0 as ly_y_item_count_pos
                    , 0.0 as ly_y_sale_count_pos
                    ,SUM(CASE WHEN spt.code in ('outgoing') THEN round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            WHEN spt.code in ('incoming') THEN -round((sm.product_uom_qty)/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2)
                            ELSE 0
                       END) as lly_item_count_pos
                    ,round(1.0/(SELECT count(pos_order_id)+1 from pos_order_res_users_rel where (pos_order_id = po.id)), 2) as lly_sale_count_pos
                from pos_order_line pol
                    inner join pos_order po on (po.id = pol.order_id)
                    inner join stock_picking sp on (sp.pos_order_id = po.id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = po.partner_id)
                    inner join product_product pp on (sm.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id)
                    inner join pos_order_res_users_rel other on (other.pos_order_id = po.id) 

                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.state='done'
                    and sm.product_id = pol.product_id
                    and pt.exclude_from_report!=True 
                GROUP BY po.id
                """) % (date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,date_to,last_yr_fiscalyear_start_date,last_yr_date_to,llyr_date_from,llyr_date_to)

        self._cr.execute(other_sql)
        other_res = self._cr.dictfetchall()
        other_sale_count = 0
        other_product_count = 0
        other_ly_m_item_count_pos = 0
        other_ly_m_sale_count_pos = 0
        other_y_item_count_pos = 0
        other_y_sale_count_pos = 0
        other_ly_y_item_count_pos = 0
        other_ly_y_sale_count_pos = 0
        other_lly_item_count_pos = 0
        other_lly_sale_count_pos = 0
        for other_value in other_res:
            other_product_count += other_value.get('net_qty', 0) or 0
            other_sale_count += other_value.get('sale_count', 0) or 0
            other_ly_m_item_count_pos += other_value.get('ly_m_item_count_pos', 0) or 0
            other_ly_m_sale_count_pos += other_value.get('ly_m_sale_count_pos', 0) or 0
            other_y_item_count_pos += other_value.get('y_item_count_pos', 0) or 0
            other_y_sale_count_pos += other_value.get('y_sale_count_pos', 0) or 0
            other_ly_y_item_count_pos += other_value.get('ly_y_item_count_pos', 0) or 0
            other_ly_y_sale_count_pos += other_value.get('ly_y_sale_count_pos', 0) or 0
            other_lly_item_count_pos += other_value.get('lly_item_count_pos', 0) or 0
            other_lly_sale_count_pos += other_value.get('lly_sale_count_pos', 0) or 0


        return sale_count + other_sale_count, product_count + other_product_count,ly_m_sale_count_pos + other_ly_m_sale_count_pos,ly_m_item_count_pos + other_ly_m_item_count_pos,y_sale_count_pos + other_y_sale_count_pos, y_item_count_pos + other_y_item_count_pos,ly_y_sale_count_pos + other_ly_y_sale_count_pos, ly_y_item_count_pos + other_ly_y_item_count_pos,lly_sale_count_pos + other_lly_sale_count_pos, lly_item_count_pos + other_lly_item_count_pos

    def get_transaction_lines(self, net_sale_list, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                              fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from):
        context = self.env.context

        salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        transaction_list = []
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids
            sale_count = ['# Sales', 'count']
            item_count = ['# Items Sold', 'count']
            items_per_transaction = ['Items Per Transaction', 'count']
            avg_sale = ['Avg $', 'amount']
            aunitsale = ['Avg Units Sale $', 'amount']

            m_sale_count, m_item_count,ly_m_sale_count,ly_m_item_count,y_sale_count,y_item_count,ly_y_sale_count ,ly_y_item_count,lly_sale_count,lly_item_count = self.with_context({'users_ids': context['options']['users_ids'] if 'options' in context else ''}).get_sale_count( str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),str(llyr_date_from), str(llyr_date_to), salesperson_ids)
            m_sale_count_pos, m_item_count_pos,ly_m_sale_count_pos, ly_m_item_count_pos,y_sale_count_pos, y_item_count_pos, ly_y_sale_count_pos, ly_y_item_count_pos, lly_sale_count_pos, lly_item_count_pos  = self.with_context({'users_ids': context['options']['users_ids'] if 'options' in context else ''}).get_sale_count_of_pos(str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),str(llyr_date_from), str(llyr_date_to),salesperson_ids)
            m_sale_count = m_sale_count + m_sale_count_pos
            m_item_count = m_item_count + m_item_count_pos
            item_per_m = m_sale_count and m_item_count / m_sale_count
            item_per_m_target = self.get_planned_values('items_per_transaction', month_start_date, date_to,
                                                        salesperson_ids)
            item_per_m_perc = item_per_m_target and (item_per_m) / item_per_m_target or 0
            m_avg_unit = m_item_count and round(net_sale_list[2] / m_item_count, 2) or 0
            m_avg_sale = m_sale_count and round(net_sale_list[2] / m_sale_count, 2) or 0

            m_sale_target = self.get_planned_values('won_no', month_start_date, date_to, salesperson_ids)
            m_item_target = self.get_planned_values('sold_item_no', month_start_date, date_to, salesperson_ids)
            m_avg_unit_target = m_item_target and round(m_item_count[3] / m_item_target, 2) or 0
            m_avg_sale_target = m_sale_target and round(net_sale_list[3] / m_sale_target, 2) or 0
            m_avg_item_per = m_sale_target and m_item_target / m_sale_target

            m_sale_perc = m_sale_target and (m_sale_count) / m_sale_target or 0
            m_item_perc = m_item_target and (m_item_count) / m_item_target or 0
            m_avg_unit_perc = m_avg_unit_target and (m_avg_unit - m_avg_unit_target) / m_avg_unit_target or 0
            m_avg_sale_perc = m_avg_sale_target and (m_avg_sale) / m_avg_sale_target or 0

            ly_m_sale_count = ly_m_sale_count + ly_m_sale_count_pos
            ly_m_item_count = ly_m_item_count + ly_m_item_count_pos
            item_per_ly = ly_m_sale_count and ly_m_item_count / ly_m_sale_count

            ly_m_avg_unit = ly_m_item_count and round(net_sale_list[5] / ly_m_item_count, 2) or 0
            ly_m_avg_sale = ly_m_sale_count and round(net_sale_list[5] / ly_m_sale_count, 2) or 0

            m_sale_inc_dec = ly_m_sale_count and (float(m_sale_count) - float(ly_m_sale_count)) / float(
                ly_m_sale_count) or 0
            m_item_inc_dec = ly_m_item_count and (m_item_count - ly_m_item_count) / ly_m_item_count or 0
            m_avg_unit_inc_dec = ly_m_avg_unit and (m_avg_unit - ly_m_avg_unit) / ly_m_avg_unit or 0
            m_avg_sale_inc_dec = ly_m_avg_sale and (m_avg_sale - ly_m_avg_sale) / ly_m_avg_sale or 0

            y_sale_count = y_sale_count + y_sale_count_pos
            y_item_count = y_item_count + y_item_count_pos
            item_per_y = y_sale_count and y_item_count / y_sale_count

            y_avg_unit = y_item_count and round(net_sale_list[7] / y_item_count, 2) or 0

            y_avg_sale = y_sale_count and round(net_sale_list[7] / y_sale_count, 2) or 0

            y_sale_target = self.get_planned_values('won_no', fiscalyear_start_date, date_to, salesperson_ids)
            y_item_target = self.get_planned_values('sold_item_no', fiscalyear_start_date, date_to, salesperson_ids)
            y_avg_unit_target = y_item_target and round(net_sale_list[7] / y_item_target, 2) or 0
            y_avg_sale_target = y_sale_target and round(net_sale_list[7] / y_sale_target, 2) or 0
            item_per_y_target = self.get_planned_values('items_per_transaction', fiscalyear_start_date, date_to,
                                                        salesperson_ids)
            item_per_y_perc = item_per_y_target and (item_per_y) / item_per_y_target or 0
            y_sale_perc = y_sale_target and (y_sale_count) / y_sale_target or 0
            y_item_perc = y_item_target and (y_item_count) / y_item_target or 0
            y_avg_unit_perc = y_avg_unit_target and (y_avg_unit) / y_avg_unit_target or 0
            y_avg_sale_perc = y_avg_sale_target and (y_avg_sale) / y_avg_sale_target or 0

            ly_y_sale_count = ly_y_sale_count + ly_y_sale_count_pos
            ly_y_item_count = ly_y_item_count + ly_y_item_count_pos

            items_per_ly_y = ly_y_sale_count and ly_y_item_count / ly_y_sale_count

            ly_y_avg_unit = ly_y_item_count and round(net_sale_list[7] / ly_y_item_count, 2) or 0
            ly_y_avg_sale = ly_y_sale_count and round(net_sale_list[7] / ly_y_sale_count, 2) or 0

            y_sale_inc_dec = ly_y_sale_count and (float(y_sale_count) - float(ly_y_sale_count)) / float(
                ly_y_sale_count) or 0
            y_item_inc_dec = ly_y_item_count and (y_item_count - ly_y_item_count) / ly_y_item_count or 0
            y_avg_unit_inc_dec = ly_y_avg_unit and (y_avg_unit - ly_y_avg_unit) / ly_y_avg_unit or 0
            y_avg_sale_inc_dec = ly_y_avg_sale and (y_avg_sale - ly_y_avg_sale) / ly_y_avg_sale or 0

            item_per_y_target_per = item_per_y_target and (item_per_y - item_per_y_target) / item_per_y_target or 0

            lly_sale_count = lly_sale_count + lly_item_count_pos
            lly_item_count = lly_item_count + lly_item_count_pos
            item_per_lly = lly_sale_count and lly_item_count / lly_sale_count

            lly_sale_target = self.get_planned_values('won_no', llyr_date_from, llyr_date_to, salesperson_ids)
            lly_item_target = self.get_planned_values('sold_item_no', llyr_date_from, llyr_date_to, salesperson_ids)
            item_per_lly_target = lly_sale_target and lly_item_target / lly_sale_target

            lly_sale_perc = lly_sale_target and (lly_sale_count) / lly_sale_target or 0
            lly_item_perc = lly_item_target and (lly_item_count) / lly_item_target or 0

            item_per_lly_target_per = item_per_lly_target and (
                    item_per_lly - item_per_lly_target) / item_per_lly_target or 0

            lly_avg_sale = lly_sale_count and round(net_sale_list[12] / lly_sale_count, 2) or 0
            lly_avg_sale_target = lly_sale_target and round(net_sale_list[12] / lly_sale_target, 2) or 0

            lly_avg_sale_perc = lly_avg_sale_target and (lly_avg_sale) / lly_avg_sale_target or 0

            lly_avg_unit = lly_item_count and round(net_sale_list[12] / lly_item_count, 2) or 0

            lly_avg_unit_target = lly_item_target and round(net_sale_list[12] / lly_item_target, 2) or 0

            lly_avg_unit_perc = lly_avg_unit_target and (lly_avg_unit) / lly_avg_unit_target or 0
            ly_sale_inc_dec = lly_sale_count and (float(ly_y_sale_count) - float(lly_sale_count)) / float(
                lly_sale_count) or 0
            ly_item_inc_dec = lly_item_count and (ly_y_item_count - lly_item_count) / lly_item_count or 0
            ly_avg_sale_inc_dec = lly_avg_sale and (ly_y_avg_sale - lly_avg_sale) / lly_avg_sale or 0
            ly_avg_unit_inc_dec = lly_avg_unit and (ly_y_avg_unit - lly_avg_unit) / lly_avg_unit or 0

            sale_count.append(m_sale_count)
            sale_count.append('')
            sale_count.append(str(round(m_sale_perc * 100, 2)) + '%' or '0.00 %')
            sale_count.append(ly_m_sale_count)
            sale_count.append(str(round(m_sale_inc_dec * 100, 2)) + '%')
            sale_count.append(y_sale_count)
            sale_count.append(y_sale_target)
            sale_count.append(str(round(y_sale_perc * 100, 2)) + '%')
            sale_count.append(ly_y_sale_count)
            sale_count.append(str(round(y_sale_inc_dec * 100, 2)) + '%')
            sale_count.append(lly_sale_count)
            sale_count.append(str(round(ly_sale_inc_dec * 100, 2)) + '%')

            item_count.append(m_item_count)
            item_count.append('')
            item_count.append(str(round(m_item_perc * 100, 2)) + '%')
            item_count.append(ly_m_item_count)
            item_count.append(str(round(m_item_inc_dec * 100, 2)) + '%')
            item_count.append(y_item_count)
            item_count.append(y_item_target)
            item_count.append(str(round(y_item_perc * 100, 2)) + '%')
            item_count.append(ly_y_item_count)
            item_count.append(str(round(y_item_inc_dec * 100, 2)) + '%')
            item_count.append(lly_item_count)
            item_count.append(str(round(ly_item_inc_dec * 100, 2)) + '%')

            m_item_per_trans_inc_dec = item_per_ly and (item_per_m - item_per_ly) / item_per_ly or 0
            y_item_per_trans_inc_dec = items_per_ly_y and (item_per_y - items_per_ly_y) / items_per_ly_y or 0
            ly_item_per_trans_inc_dec = item_per_lly and (items_per_ly_y - item_per_lly) / item_per_lly or 0
            items_per_transaction.append(item_per_m)
            items_per_transaction.append(str(round(item_per_m_target, 2)))
            items_per_transaction.append(str(round(item_per_m_perc * 100, 2)) + '%')
            items_per_transaction.append(item_per_ly)
            items_per_transaction.append(str(round(m_item_per_trans_inc_dec * 100, 2)) + '%')
            items_per_transaction.append(item_per_y)
            items_per_transaction.append(item_per_y_target)
            items_per_transaction.append(str(round(item_per_y_perc * 100, 2)) + '%')
            items_per_transaction.append(items_per_ly_y)
            items_per_transaction.append(str(round(y_item_per_trans_inc_dec * 100, 2)) + '%')
            items_per_transaction.append(item_per_lly)
            items_per_transaction.append(str(round(ly_item_per_trans_inc_dec * 100, 2)) + '%')

            avg_sale.append(m_avg_sale)
            avg_sale.append('')
            avg_sale.append(str(round(m_avg_sale_perc * 100, 2)) + '%')
            avg_sale.append(ly_m_avg_sale)
            avg_sale.append(str(round(m_avg_sale_inc_dec * 100, 2)) + '%')
            avg_sale.append(y_avg_sale)
            avg_sale.append(y_avg_sale_target)
            avg_sale.append(str(round(y_avg_sale_perc * 100, 2)) + '%')
            avg_sale.append(ly_y_avg_sale)
            avg_sale.append(str(round(y_avg_sale_inc_dec * 100, 2)) + '%')
            avg_sale.append(lly_avg_sale)
            avg_sale.append(str(round(ly_avg_sale_inc_dec * 100, 2)) + '%')

            aunitsale.append(m_avg_unit)
            aunitsale.append('')
            aunitsale.append(str(round(m_avg_unit_perc * 100, 2)) + '%')
            aunitsale.append(ly_m_avg_unit)
            aunitsale.append(str(round(m_avg_unit_inc_dec * 100, 2)) + '%')
            aunitsale.append(y_avg_unit)
            aunitsale.append(y_avg_unit_target)
            aunitsale.append(str(round(y_avg_unit_perc * 100, 2)) + '%')
            aunitsale.append(ly_y_avg_unit)
            aunitsale.append(str(round(y_avg_unit_inc_dec * 100, 2)) + '%')
            aunitsale.append(lly_avg_unit)
            aunitsale.append(str(round(ly_avg_unit_inc_dec * 100, 2)) + '%')

            transaction_list.append(sale_count)
            transaction_list.append(item_count)
            transaction_list.append(items_per_transaction)
            transaction_list.append(avg_sale)
            transaction_list.append(aunitsale)
        return transaction_list

    def format_value_original(self, value):
        if value == 0:
            return ''
        else:
            fmt = '%.2f'
            lang_code = self._context.get('lang') or 'en_US'
            lang = self.env['res.lang']._lang_get(lang_code)
            formatted_amount = lang.format(
                fmt, value, grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'\u2011')
            return formatted_amount

    def format_value_percent(self, value):
        if value == 0:
            return ''
        else:
            fmt = '%.2f'
            lang_code = self._context.get('lang') or 'en_US'
            lang = self.env['res.lang']._lang_get(lang_code)
            formatted_amount = lang.format(
                fmt, value, grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'\u2011')

            return formatted_amount

    def update_symbols(self, values):
        list = values[2:]
        new_list = []
        index = [2, 3, 5, 7, 8, 10, 12]
        for x in list:
            if isinstance(x, (float, int)):

                if float(x) < 0.0:
                    new_x = '(' + str(self.format_value_original(abs(float(x)))) + ')'
                # elif values[0] in ['Base (3% * gross margin $)', 'Goal (6% * gross margin $)',
                #                    'Stretch (9% * gross margin $)', 'Average Units per Sale']:
                #     new_x = self.format_value_original(float(x))
                elif values[0] in ['# Sales', '# Items Sold', 'Opportunity #',
                                   'Won #', 'Lost #', 'Calls', 'SMS/MMS', 'Emails', 'New Contacts',
                                   'Total Contacts']:
                    fmt = '%.0f'
                    lang_code = self._context.get('lang') or 'en_US'
                    lang = self.env['res.lang']._lang_get(lang_code)
                    new_x = lang.format(
                        fmt, int(x), grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}').replace(
                        r'-', u'\u2011')
                else:
                    new_x = self.format_value_original(float(x))

            elif isinstance(x, string_types):
                if '%' in x:

                    tmp_x = x.replace("%", "")
                    if float(tmp_x) < 0.0:
                        new_x = '(' + str(self.format_value_percent(abs(float(tmp_x)))) + ')%'
                    elif float(tmp_x) > 0.0:
                        new_x = str(self.format_value_percent(float(tmp_x))) + '%'
                    elif float(tmp_x) == 0.0:
                        new_x = ''

                else:
                    new_x = x
            new_list.append(new_x)
        if values[1] == 'amount':

            for i in index:
                if new_list[i - 2] != '':
                    new_list[i - 2] = '$ ' + str(new_list[i - 2])

        final_list = [{'name': k} for k in new_list]

        return final_list

    def get_repair_amount(self, date_from, date_to, salesperson_ids, sale_type='sale', check_delivery=None):

        ids = ''
        context = self.env.context
        salesperson = salesperson_ids
        if salesperson:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        account_repair = self.env['account.account'].search([('code', '=', '401000')]).id
        account_jewel = self.env['account.account'].search([('code', '=', '401010')]).id
        account = '(' + str(account_repair) + ',' + str(account_jewel) + ')'

        sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as repair_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id in %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account, date_from, date_to)
        if ids:
            sql += (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        repair_sale = 0
        for value in result:
            repair_sale += value.get('repair_price', 0) or 0

        jewel_repair_disc = self.env['account.account'].search([('code', '=', '451000')]).id
        watch_repair_dics = self.env['account.account'].search([('code', '=', '451010')]).id
        disc_account = '(' + str(jewel_repair_disc) + ',' + str(watch_repair_dics) + ')'

        sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as repair_disc_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id in %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (disc_account, date_from, date_to)
        if ids:
            sql += (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        repair_disc_price = 0
        for value in result:
            repair_disc_price += value.get('repair_disc_price', 0) or 0

        return repair_sale - repair_disc_price

    def get_repair_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                         fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from):
        context = self.env.context
        # import pdb;pdb.set_trace()

        salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        sales_list = []

        if salesperson_ids:
            state_domain = [('state', 'in', ['sale', 'done']), ('order_id.user_id', 'in', salesperson_ids), ]
            sale_type_domain = [('product_id.categ_id.sale_type', '=', 'sale'),
                                ('product_id.exclude_from_report', '=', False)]
            domain = state_domain + sale_type_domain
            retail_sale = ['Repairs Sold', 'amount']

            mnth_repair_amount = self.get_repair_amount(str(month_start_date), date_to, salesperson_ids,
                                                        check_delivery=True)

            mnth_retail_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                       salesperson_ids)

            mnth_retail_perc = mnth_retail_plan and (mnth_repair_amount) / mnth_retail_plan or 0.00

            ly_mnth_retail_amount = self.get_repair_amount(str(last_yr_month_start_date), str(last_yr_date_to),
                                                           salesperson_ids, check_delivery=True)

            mnth_retail_inc_dec = ly_mnth_retail_amount and (
                    mnth_repair_amount - ly_mnth_retail_amount) / ly_mnth_retail_amount or 0

            yr_retail_amount = self.get_repair_amount(str(fiscalyear_start_date), date_to, salesperson_ids,
                                                      check_delivery=True)
            yr_retail_plan = self.get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                     salesperson_ids)
            yr_retail_perc = yr_retail_plan and (yr_retail_amount) / yr_retail_plan or 0

            ly_yr_retail_amount = self.get_repair_amount(str(last_yr_fiscalyear_start_date), str(last_yr_date_to),
                                                         salesperson_ids, check_delivery=True)

            yr_retail_inc_dec = ly_yr_retail_amount and (
                    yr_retail_amount - ly_yr_retail_amount) / ly_yr_retail_amount or 0

            llyr_retail_amount = self.get_repair_amount(str(llyr_date_from), llyr_date_to, salesperson_ids,
                                                        check_delivery=True)

            llyr_retail_plan = self.get_planned_values('retail_sale_amount', llyr_date_from, llyr_date_to,
                                                       salesperson_ids)
            llyr_retail_perc = llyr_retail_plan and (llyr_retail_amount) / llyr_retail_plan or 0

            retail_sale.append(mnth_repair_amount)
            retail_sale.append('')
            retail_sale.append('0.00')
            retail_sale.append(str(round(mnth_retail_perc * 100, 2)) + '%')
            retail_sale.append(ly_mnth_retail_amount)
            retail_sale.append(str(round(mnth_retail_inc_dec * 100, 2)) + '%')
            retail_sale.append(yr_retail_amount)
            retail_sale.append('0.00')
            retail_sale.append(str(round(yr_retail_perc * 100, 2)) + '%')
            retail_sale.append(ly_yr_retail_amount)
            retail_sale.append(str(round(yr_retail_inc_dec * 100, 2)) + '%')
            retail_sale.append(llyr_retail_amount)
            retail_sale.append(llyr_retail_plan)
            retail_sale.append(str(round(llyr_retail_perc * 100, 2)) + '%')

            sales_list.append(retail_sale)

            # gross margin $

            retail_gross_sale = ['Gross Margin $', 'amount']

            mnth_repair_gross_amount = self.get_repair_gross_amount(str(month_start_date), date_to, salesperson_ids,
                                                                    check_delivery=True)
            mnth_retail_gross_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                             salesperson_ids)
            mnth_retail_gross_perc = mnth_retail_gross_plan and (
                mnth_repair_gross_amount) / mnth_retail_gross_plan or 0

            ly_mnth_retail_gross_amount = self.get_repair_gross_amount(str(last_yr_month_start_date),
                                                                       str(last_yr_date_to), salesperson_ids,
                                                                       check_delivery=True)
            mnth_retail_gross_inc_dec = ly_mnth_retail_gross_amount and (
                    mnth_repair_gross_amount - ly_mnth_retail_gross_amount) / ly_mnth_retail_gross_amount or 0

            yr_retail_gross_amount = self.get_repair_gross_amount(str(fiscalyear_start_date), date_to,
                                                                  salesperson_ids, check_delivery=True)

            llyr_retail_gross_amount = self.get_repair_gross_amount(str(llyr_date_from), llyr_date_to,
                                                                    salesperson_ids, check_delivery=True)

            yr_retail_gross_plan = self.get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                           salesperson_ids)

            llyr_retail_gross_plan = self.get_planned_values('retail_sale_amount', llyr_date_from, llyr_date_to,
                                                             salesperson_ids)
            yr_retail_gross_perc = yr_retail_gross_plan and (yr_retail_gross_amount) / yr_retail_gross_plan or 0

            llyr_retail_gross_perc = llyr_retail_gross_plan and (
                llyr_retail_gross_amount) / llyr_retail_gross_plan or 0

            ly_yr_retail_gross_amount = self.get_repair_gross_amount(str(last_yr_fiscalyear_start_date),
                                                                     str(last_yr_date_to), salesperson_ids,
                                                                     check_delivery=True)

            yr_retail_gross_inc_dec = ly_yr_retail_gross_amount and (
                    yr_retail_gross_amount - ly_yr_retail_gross_amount) / ly_yr_retail_gross_amount or 0

            retail_gross_sale.append(mnth_repair_gross_amount)
            retail_gross_sale.append('')
            retail_gross_sale.append('0.00')
            retail_gross_sale.append(str(round(mnth_retail_gross_perc * 100, 2)) + '%')
            retail_gross_sale.append(ly_mnth_retail_gross_amount)
            retail_gross_sale.append(str(round(mnth_retail_gross_inc_dec * 100, 2)) + '%')
            retail_gross_sale.append(yr_retail_gross_amount)
            retail_gross_sale.append('0.00')
            retail_gross_sale.append(str(round(yr_retail_gross_perc * 100, 2)) + '%')
            retail_gross_sale.append(ly_yr_retail_gross_amount)
            retail_gross_sale.append(str(round(yr_retail_gross_inc_dec * 100, 2)) + '%')
            retail_gross_sale.append(llyr_retail_gross_amount)
            retail_gross_sale.append(llyr_retail_gross_plan)
            retail_gross_sale.append(str(round(llyr_retail_gross_perc * 100, 2)) + '%')

            sales_list.append(retail_gross_sale)

            gross_percentage = self.get_repair_gross_percentage(retail_gross_sale, retail_sale, month_start_date,
                                                                fiscalyear_start_date, date_to, salesperson_ids,
                                                                llyr_date_to, llyr_date_from)
            sales_list.append(gross_percentage)
        return sales_list

    def get_repair_gross_amount(self, date_from, date_to, salesperson_ids, sale_type='sale', check_delivery=None):
        ids = ''
        context = self.env.context
        salesperson = salesperson_ids
        if salesperson:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        # jewelry part calc
        account_jewelry_repair = self.env['account.account'].search([('code', '=', '401000')]).id
        # account_watch_repaie = self.env['account.account'].search([('code', '=', '401010')]).id

        sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as jewel_repair_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id in %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account_jewelry_repair, date_from, date_to)

        if ids:
            sql += (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        jewel_repair_price = 0
        for value in result:
            jewel_repair_price += value.get('jewel_repair_price', 0) or 0

        # jewel_disc
        account_jewelry_repair_disc = self.env['account.account'].search([('code', '=', '451000')]).id

        jwel_disc_sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as jewelry_repair_disc
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id = %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account_jewelry_repair_disc, date_from, date_to)

        if ids:
            jwel_disc_sql += (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(jwel_disc_sql)
        jwel_disc_sql_result = self._cr.dictfetchall()

        jewelry_repair_disc = 0
        for value in jwel_disc_sql_result:
            jewelry_repair_disc += value.get('jewelry_repair_disc', 0) or 0

        account_jewel_cod = self.env['account.account'].search([('code', '=', '501000')]).id

        cod_jewel_repair_sql = ("""
            select sum(aml.debit - aml.credit) as cod_jewel_repair_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id = %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account_jewel_cod, date_from, date_to)
        if ids:
            cod_jewel_repair_sql += (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(cod_jewel_repair_sql)
        cod_jewel_repair_sql_result = self._cr.dictfetchall()

        cod_jewel_repair_price = 0
        for value in cod_jewel_repair_sql_result:
            cod_jewel_repair_price += value.get('cod_jewel_repair_price', 0) or 0

        jwel_total = ((jewel_repair_price - jewelry_repair_disc) * (0.3)) - cod_jewel_repair_price

        # watch part calc
        account_watch_repair = self.env['account.account'].search([('code', '=', '401010')]).id
        watch_repair_sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as watch_repair_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id = %s and
                aml.date >= '%s' and aml.date <= '%s' and ai.invoice_user_id in %s
            """) % (account_watch_repair, date_from, date_to)
        if ids:
            watch_repair_sql += " and ai.invoice_user_id in %s" % ids

        self._cr.execute(watch_repair_sql)
        watch_repair_result = self._cr.dictfetchall()

        watch_repair_price = 0
        for value in watch_repair_result:
            watch_repair_price += value.get('watch_repair_price', 0) or 0

        # watch_disc
        account_watch_repair_disc = self.env['account.account'].search([('code', '=', '451010')]).id
        watch_disc_sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as watch_repair_disc

            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id = %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account_watch_repair_disc, date_from, date_to)
        if ids:
            watch_disc_sql += " and ai.invoice_user_id in %s" % ids

        self._cr.execute(watch_disc_sql)
        watch_disc_sql_result = self._cr.dictfetchall()

        watch_repair_disc = 0
        for value in watch_disc_sql_result:
            watch_repair_disc += value.get('watch_repair_disc', 0) or 0

        # cost of watch
        account_watch_cod = self.env['account.account'].search([('code', '=', '501010')]).id

        cod_watch_repair_sql = ("""
            select sum(aml.debit - aml.credit) as cod_watch_repair_price

            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id = %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account_watch_cod, date_from, date_to)
        if ids:
            cod_watch_repair_sql = (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(cod_watch_repair_sql)
        cod_watch_repair_sql_result = self._cr.dictfetchall()

        cod_watch_repair_price = 0
        for value in cod_watch_repair_sql_result:
            cod_watch_repair_price += value.get('cod_watch_repair_price', 0) or 0

        watch_total = (watch_repair_price - watch_repair_disc) - cod_watch_repair_price

        account_repair = self.env['account.account'].search([('code', '=', '501000')]).id
        account_jewel = self.env['account.account'].search([('code', '=', '501010')]).id

        account = '(' + str(account_repair) + ',' + str(account_jewel) + ')'

        sql = ("""
            select sum(aml.debit) as repair_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id in %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account, date_from, date_to)
        if ids:
            sql = (" and ai.invoice_user_id in %s") % ids

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        repair_sale = 0
        for value in result:
            repair_sale += value.get('repair_price', 0) or 0

        return jwel_total + watch_total

    def get_repair_gross_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                               fiscalyear_start_date, last_yr_fiscalyear_start_date):
        context = self.env.context
        # import pdb;pdb.set_trace()

        salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        sales_list = []
        # import pdb;pdb.set_trace()

        if salesperson_ids:
            state_domain = [('state', 'in', ['sale', 'done']), ('order_id.user_id', 'in', salesperson_ids), ]
            sale_type_domain = [('product_id.categ_id.sale_type', '=', 'sale'),
                                ('product_id.exclude_from_report', '=', False)]
            domain = state_domain + sale_type_domain
            retail_gross_sale = ['Gross Margin $', 'amount']

            mnth_repair_gross_amount = self.get_repair_gross_amount(str(month_start_date), date_to, salesperson_ids,
                                                                    check_delivery=True)
            mnth_retail_gross_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                             salesperson_ids)
            mnth_retail_gross_perc = mnth_retail_gross_plan and (
                mnth_repair_gross_amount) / mnth_retail_gross_plan or 0

            ly_mnth_retail_gross_amount = self.get_repair_gross_amount(str(last_yr_month_start_date),
                                                                       str(last_yr_date_to), salesperson_ids,
                                                                       check_delivery=True)

            # ly_mnth_so_return_amount, ly_mnth_so_return_cost,  = self.get_so_return_amount(salesperson_ids,
            #                                                                              str(last_yr_month_start_date),
            #                                                                              str(last_yr_date_to))
            mnth_retail_gross_inc_dec = ly_mnth_retail_gross_amount and (
                    mnth_repair_gross_amount - ly_mnth_retail_gross_amount) / ly_mnth_retail_gross_amount or 0

            yr_retail_gross_amount = self.get_repair_gross_amount(str(fiscalyear_start_date), date_to,
                                                                  salesperson_ids,
                                                                  check_delivery=True)

            yr_retail_gross_plan = self.get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                           salesperson_ids)
            yr_retail_gross_perc = yr_retail_gross_plan and (yr_retail_gross_amount) / yr_retail_gross_plan or 0

            ly_yr_retail_gross_amount = self.get_repair_gross_amount(str(last_yr_fiscalyear_start_date),
                                                                     str(last_yr_date_to), salesperson_ids,
                                                                     check_delivery=True)

            yr_retail_gross_inc_dec = ly_yr_retail_gross_amount and (
                    yr_retail_gross_amount - ly_yr_retail_gross_amount) / ly_yr_retail_gross_amount or 0

        return sales_list

    # service
    def get_service_amount(self, date_from, date_to, salesperson_ids, sale_type='sale', check_delivery=None):
        ids = ''
        salesperson = salesperson_ids
        if salesperson:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        # retail_sale = 0.0
        # invoice_sale = 0.0
        # gross_margin = 0.0

        account_service = self.env['account.account'].search([('code', '=', '402000')]).id
        account_ship_service = self.env['account.account'].search([('code', '=', '402070')]).id

        ########
        account = '(' + str(account_service) + ',' + str(account_ship_service) + ')'

        sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as service_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') 
                and aml.account_id in %s 
                and aml.date >= '%s' 
                and aml.date <= '%s' 
            """) % (account, date_from, date_to)
        if ids:
            sql += " and ai.invoice_user_id in %s" % id
        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        service_sale = 0.0
        for value in result:
            service_sale += value.get('service_price', 0.0) or 0.0

        ########
        account_service = self.env['account.account'].search([('code', '=', '452000')]).id

        sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as service_dis_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') 
                and aml.account_id = %s 
                and aml.date >= '%s' 
                and aml.date <= '%s' 
            """) % (account_service, date_from, date_to)
        if ids:
            sql += " and ai.invoice_user_id in %s" % ids
        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        service_dis_price = 0
        for value in result:
            service_dis_price += value.get('service_dis_price', 0) or 0

        return service_sale - service_dis_price

    def get_service_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                          fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from):
        context = self.env.context

        salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        sales_list = []
        # import pdb;pdb.set_trace()

        if salesperson_ids:
            state_domain = [('state', 'in', ['sale', 'done']), ('order_id.user_id', 'in', salesperson_ids), ]
            sale_type_domain = [('product_id.categ_id.sale_type', '=', 'sale'),
                                ('product_id.exclude_from_report', '=', False)]
            domain = state_domain + sale_type_domain
            service_sale = ['Service Sold', 'amount']

            mnth_repair_amount = self.get_service_amount(str(month_start_date), date_to, salesperson_ids,
                                                         check_delivery=True)

            mnth_retail_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                       salesperson_ids)
            mnth_retail_perc = mnth_retail_plan and (mnth_repair_amount) / mnth_retail_plan or 0

            ly_mnth_retail_amount = self.get_service_amount(str(last_yr_month_start_date), str(last_yr_date_to),
                                                            salesperson_ids, check_delivery=True)

            # (ly_mnth_so_return_amount,
            #  ly_mnth_so_return_cost) = self.get_so_return_amount(salesperson_ids, str(last_yr_month_start_date),
            #                                                      str(last_yr_date_to))
            mnth_retail_inc_dec = ly_mnth_retail_amount and (
                    mnth_repair_amount - ly_mnth_retail_amount) / ly_mnth_retail_amount or 0

            yr_retail_amount = self.get_service_amount(str(fiscalyear_start_date), date_to, salesperson_ids,
                                                       check_delivery=True)
            llyr_retail_amount = self.get_service_amount(str(llyr_date_from), llyr_date_to, salesperson_ids,
                                                         check_delivery=True)

            yr_retail_plan = self.get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                     salesperson_ids)
            yr_retail_perc = yr_retail_plan and (yr_retail_amount) / yr_retail_plan or 0

            llyr_retail_plan = self.get_planned_values('retail_sale_amount', llyr_date_from, llyr_date_to,
                                                       salesperson_ids)

            llyr_retail_perc = llyr_retail_plan and (llyr_retail_amount) / llyr_retail_plan or 0

            ly_yr_retail_amount = self.get_service_amount(str(last_yr_fiscalyear_start_date), str(last_yr_date_to),
                                                          salesperson_ids, check_delivery=True)

            yr_retail_inc_dec = ly_yr_retail_amount and (
                    yr_retail_amount - ly_yr_retail_amount) / ly_yr_retail_amount or 0

            service_sale.append(mnth_repair_amount)
            service_sale.append('')
            service_sale.append('0.00')
            service_sale.append(str(round(mnth_retail_perc * 100, 2)) + '%')
            service_sale.append(ly_mnth_retail_amount)
            service_sale.append(str(round(mnth_retail_inc_dec * 100, 2)) + '%')
            service_sale.append(yr_retail_amount)
            service_sale.append('0.00')
            service_sale.append(str(round(yr_retail_perc * 100, 2)) + '%')
            service_sale.append(ly_yr_retail_amount)
            service_sale.append(str(round(yr_retail_inc_dec * 100, 2)) + '%')
            service_sale.append(llyr_retail_amount)
            service_sale.append(llyr_retail_plan)
            service_sale.append(str(round(llyr_retail_perc * 100, 2)) + '%')

            sales_list.append(service_sale)

            ##################
            # gross margin $
            service_gross = ['Gross Margin $', 'amount']

            mnth_repair_gross_amount = self.get_service_gross_amount(str(month_start_date), date_to,
                                                                     salesperson_ids, check_delivery=True)

            mnth_retail_gross_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                             salesperson_ids)
            mnth_retail_gross_perc = mnth_retail_gross_plan and (
                mnth_repair_gross_amount) / mnth_retail_gross_plan or 0

            ly_mnth_retail_gross_amount = self.get_service_gross_amount(str(last_yr_month_start_date),
                                                                        str(last_yr_date_to), salesperson_ids,
                                                                        check_delivery=True)
            mnth_retail_inc_dec = ly_mnth_retail_gross_amount and (
                    mnth_repair_gross_amount - ly_mnth_retail_gross_amount) / ly_mnth_retail_gross_amount or 0

            yr_retail_gross_amount = self.get_service_gross_amount(str(fiscalyear_start_date), date_to,
                                                                   salesperson_ids, check_delivery=True)

            llyr_retail_gross_amount = self.get_service_gross_amount(str(llyr_date_from), llyr_date_to,
                                                                     salesperson_ids, check_delivery=True)

            llyr_retail_gross_plan = self.get_planned_values('retail_sale_amount', llyr_date_from, llyr_date_to,
                                                             salesperson_ids)
            llyr_retail_gross_perc = llyr_retail_gross_plan and (
                llyr_retail_gross_amount) / llyr_retail_gross_plan or 0

            yr_retail_gross_plan = self.get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                           salesperson_ids)
            yr_retail_gross_perc = yr_retail_gross_plan and (yr_retail_gross_amount) / yr_retail_gross_plan or 0

            ly_yr_retail_gross_amount = self.get_service_gross_amount(str(last_yr_fiscalyear_start_date),
                                                                      str(last_yr_date_to), salesperson_ids,
                                                                      check_delivery=True)

            yr_retail_gross_inc_dec = ly_yr_retail_gross_amount and (
                    yr_retail_gross_amount - ly_yr_retail_gross_amount) / ly_yr_retail_gross_amount or 0

            service_gross.append(mnth_repair_gross_amount)
            service_gross.append('')
            service_gross.append('0.00')
            service_gross.append(str(round(mnth_retail_gross_perc * 100, 2)) + '%')
            service_gross.append(ly_mnth_retail_gross_amount)
            service_gross.append(str(round(mnth_retail_inc_dec * 100, 2)) + '%')
            service_gross.append(yr_retail_gross_amount)
            service_gross.append('0.00')
            service_gross.append(str(round(yr_retail_gross_perc * 100, 2)) + '%')
            service_gross.append(ly_yr_retail_gross_amount)
            service_gross.append(str(round(yr_retail_gross_inc_dec * 100, 2)) + '%')
            service_gross.append(llyr_retail_gross_amount)
            service_gross.append(llyr_retail_gross_plan)
            service_gross.append(str(round(llyr_retail_gross_perc * 100, 2)) + '%')

            sales_list.append(service_gross)

            gross_percentage = self.get_repair_gross_percentage(
                service_gross, service_sale, month_start_date, fiscalyear_start_date, date_to, salesperson_ids,
                llyr_date_to, llyr_date_from)

            sales_list.append(gross_percentage)
        return sales_list

    def get_service_gross_amount(self, date_from, date_to, salesperson_ids, sale_type='sale', check_delivery=None):

        ids = ''

        context = self.env.context
        salesperson = salesperson_ids
        if salesperson:
            salesperson_str = ','.join(str(x) for x in salesperson_ids)
            ids = '(' + salesperson_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        retail_sale = 0
        invoice_sale = 0
        gross_margin = 0

        # service part calc

        account_service = self.env['account.account'].search([('code', '=', '402000')]).id
        account_ship = self.env['account.account'].search([('code', '=', '402070')]).id
        account = '(' + str(account_service) + ',' + str(account_ship) + ')'
        # account = '(' + str(account_repair) + ',' + str(account_jewel) + ')'
        # import pdb;pdb.set_trace()

        sql = ("""
            select (sum(aml.credit) - sum(aml.debit)) as service_sale_price
            from account_move_line aml
                inner join account_move ai on (ai.id = aml.move_id)
            where aml.parent_state in ('posted') and aml.account_id in %s and
                aml.date >= '%s' and aml.date <= '%s'
            """) % (account, date_from, date_to)
        if ids:
            sql += " and ai.invoice_user_id in %s" % ids
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        service_sale_price = 0
        for value in result:
            service_sale_price += value.get('service_sale_price', 0) or 0

        ############ service_disc
        account_service_disc = self.env['account.account'].search([('code', '=', '452000')]).id

        service_disc_sql = ("""
                        select (sum(aml.credit) - sum(aml.debit)) as service_price_disc
                        from account_move_line aml
                            inner join account_move ai on (ai.id = aml.move_id)
                        where aml.parent_state in ('posted') and aml.account_id = %s and
                            aml.date >= '%s' and aml.date <= '%s'
                        """) % (account_service_disc, date_from, date_to)

        if ids:
            sql += " and ai.invoice_user_id in %s" % ids

        self._cr.execute(service_disc_sql)
        service_disc_sql_result = self._cr.dictfetchall()

        service_price_disc = 0
        for value in service_disc_sql_result:
            service_price_disc += value.get('service_price_disc', 0) or 0

        account_service_cod = self.env['account.account'].search([('code', '=', '502000')]).id
        account_ship_cod = self.env['account.account'].search([('code', '=', '580020')]).id
        account = '(' + str(account_service_cod) + ',' + str(account_ship_cod) + ')'
        # import pdb;pdb.set_trace()

        cod_service_sql = ("""
                        select sum(aml.debit - aml.credit) as cod_service_price
                        from account_move_line aml
                            inner join account_move ai on (ai.id = aml.move_id)
                        where aml.parent_state in ('posted') and aml.account_id in %s and
                            aml.date >= '%s' and aml.date <= '%s'
                        """) % (account, date_from, date_to)

        if ids:
            cod_service_sql = " and ai.invoice_user_id in %s" % ids

        self._cr.execute(cod_service_sql)
        cod_service_sql_result = self._cr.dictfetchall()

        cod_service_price = 0
        for value in cod_service_sql_result:
            cod_service_price += value.get('cod_service_price', 0) or 0

        service_total = ((service_sale_price + service_price_disc)) - cod_service_price

        return service_total

    def get_service_gross_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                                fiscalyear_start_date, last_yr_fiscalyear_start_date):
        context = self.env.context
        # import pdb;pdb.set_trace()

        salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        sales_list = []
        # import pdb;pdb.set_trace()

        if salesperson_ids:
            state_domain = [('state', 'in', ['sale', 'done']), ('order_id.user_id', 'in', salesperson_ids), ]
            sale_type_domain = [('product_id.categ_id.sale_type', '=', 'sale'),
                                ('product_id.exclude_from_report', '=', False)]
            domain = state_domain + sale_type_domain
            service_gross = ['Gross Margin $', 'amount']

            mnth_repair_gross_amount = self.get_service_gross_amount(str(month_start_date), date_to,
                                                                     salesperson_ids,
                                                                     check_delivery=True)
            mnth_retail_gross_plan = self.get_planned_values('retail_sale_amount', month_start_date, date_to,
                                                             salesperson_ids)
            mnth_retail_gross_perc = mnth_retail_gross_plan and (
                mnth_repair_gross_amount) / mnth_retail_gross_plan or 0

            ly_mnth_retail_gross_amount = self.get_service_gross_amount(str(last_yr_month_start_date),
                                                                        str(last_yr_date_to), salesperson_ids,
                                                                        check_delivery=True)

            mnth_retail_inc_dec = ly_mnth_retail_gross_amount and (
                    mnth_repair_gross_amount - ly_mnth_retail_gross_amount) / ly_mnth_retail_gross_amount or 0

            yr_retail_gross_amount = self.get_service_gross_amount(str(fiscalyear_start_date), date_to,
                                                                   salesperson_ids,
                                                                   check_delivery=True)

            yr_retail_gross_plan = self.get_planned_values('retail_sale_amount', fiscalyear_start_date, date_to,
                                                           salesperson_ids)
            yr_retail_gross_perc = yr_retail_gross_plan and (yr_retail_gross_amount) / yr_retail_gross_plan or 0

            ly_yr_retail_gross_amount = self.get_service_gross_amount(str(last_yr_fiscalyear_start_date),
                                                                      str(last_yr_date_to), salesperson_ids,
                                                                      check_delivery=True)
            yr_retail_gross_inc_dec = ly_yr_retail_gross_amount and (
                    yr_retail_gross_amount - ly_yr_retail_gross_amount) / ly_yr_retail_gross_amount or 0

            service_gross.append(mnth_repair_gross_amount)
            service_gross.append('')
            service_gross.append('0.00')
            service_gross.append(str(round(mnth_retail_gross_perc * 100, 2)) + '%')
            service_gross.append(ly_mnth_retail_gross_amount)
            service_gross.append(str(round(mnth_retail_inc_dec * 100, 2)) + '%')
            service_gross.append(yr_retail_gross_amount)
            service_gross.append('0.00')
            service_gross.append(str(round(yr_retail_gross_perc * 100, 2)) + '%')
            service_gross.append(ly_yr_retail_gross_amount)
            service_gross.append(str(round(yr_retail_gross_inc_dec * 100, 2)) + '%')

            sales_list.append(service_gross)

        return sales_list

    def _get_stagewise_crm_lines(self, goal_for, salesperson_ids, opportunity_no, opportunity_amount,
                                 month_start_date,
                                 date_to, last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                 last_yr_fiscalyear_start_date, domain, stage_clause, llyr_date_to, llyr_date_from):

        date_clause1 = [('create_date', '>=', month_start_date), ('create_date', '<=', date_to)]
        date_clause2 = [('create_date', '>=', str(last_yr_month_start_date)),
                        ('create_date', '<=', str(last_yr_date_to))]
        date_clause3 = [('create_date', '>=', str(fiscalyear_start_date)), ('create_date', '<=', date_to)]
        date_clause4 = [('create_date', '>=', str(last_yr_fiscalyear_start_date)),
                        ('create_date', '<=', str(last_yr_date_to))]
        date_clause5 = [('create_date', '>=', str(llyr_date_from)),
                        ('create_date', '<=', str(llyr_date_to))]

        avg_days_closed = ['Avg Days to Close', 'count']
        mnth_opportunities = self.env['crm.lead'].search(domain + date_clause1 + stage_clause)
        mnth_opportunities_count = mnth_opportunities and len(mnth_opportunities) or 0

        opportunity_no.append(mnth_opportunities_count)
        target = self.get_planned_values(goal_for, month_start_date, date_to, salesperson_ids)
        if goal_for == 'loss_no':
            oppo_target = self.get_planned_values('opportunity_no', month_start_date, date_to, salesperson_ids)
            won_target = self.get_planned_values('won_no', month_start_date, date_to, salesperson_ids)
            target = (oppo_target - won_target) > 0 and (oppo_target - won_target) or 0
        # opportunity_no.append(target)
        plan_m = target and (mnth_opportunities_count) / target or 0
        opportunity_no.append('')
        opportunity_no.append(str(round(plan_m * 100, 2)) + '%')

        mnth_amount = 0
        mnth_avg_days = 0
        day_close = 0
        for x in mnth_opportunities:
            mnth_amount += x.expected_revenue
            if goal_for == 'won_no':
                day_close += x.day_close

        team_target = 0

        if goal_for == 'won_no':
            team_target = self.get_planned_values('won_amount', month_start_date, date_to, salesperson_ids)

            closing_target = self.get_planned_values('avg_closing_date', month_start_date, date_to, salesperson_ids)
            mnth_avg_days = mnth_opportunities_count and day_close and day_close / mnth_opportunities_count or 0
            avg_days_closed.append(str(round(mnth_avg_days, 2)) + ' days')
            # avg_days_closed.append(str(closing_target) + ' days')
            mnth_closing_plan = closing_target and (mnth_avg_days) / closing_target or 0
            avg_days_closed.append('')
            avg_days_closed.append(str(round(mnth_closing_plan * 100, 2)))

        elif goal_for == 'loss_no':
            team_target = self.get_planned_values('loss_amount', month_start_date, date_to, salesperson_ids)

        opportunity_amount.append(mnth_amount)
        # opportunity_amount.append(team_target)
        m_plan_amount = team_target and (mnth_amount) / team_target or 0
        opportunity_amount.append('')
        opportunity_amount.append(str(round(m_plan_amount * 100, 2)) + '%')

        last_yr_mnth_opportunities = self.env['crm.lead'].search(domain + stage_clause + date_clause2)
        last_yr_mnth_opportunities_count = last_yr_mnth_opportunities and len(last_yr_mnth_opportunities) or 0

        opportunity_no.append(last_yr_mnth_opportunities_count)
        inc_dec_m = last_yr_mnth_opportunities_count and (
                float(mnth_opportunities_count) - float(last_yr_mnth_opportunities_count)) / float(
            last_yr_mnth_opportunities_count) or 0
        opportunity_no.append(str(round(inc_dec_m * 100, 2)) + '%')

        last_yr_mnth_amount = 0
        last_yr_mnth_avg_days = 0
        last_yr_mnth_day_close = 0
        for x in last_yr_mnth_opportunities:
            last_yr_mnth_amount += x.expected_revenue
            last_yr_mnth_day_close += x.day_close

        if goal_for == 'won_no':
            last_yr_mnth_avg_days = last_yr_mnth_opportunities_count and last_yr_mnth_day_close and (
                    last_yr_mnth_day_close / last_yr_mnth_opportunities_count) or 0
            avg_days_closed.append(str(round(last_yr_mnth_avg_days, 2)) + ' days')
            m_inc_dec_avg_days = last_yr_mnth_avg_days and (
                    mnth_avg_days - last_yr_mnth_avg_days) / last_yr_mnth_avg_days or 0
            avg_days_closed.append(str(round(m_inc_dec_avg_days * 100, 2)))

        opportunity_amount.append(last_yr_mnth_amount)
        m_inc_dec_amount = last_yr_mnth_amount and (mnth_amount - last_yr_mnth_amount) / last_yr_mnth_amount or 0
        opportunity_amount.append(str(round(m_inc_dec_amount * 100, 2)) + '%')
        target = self.get_planned_values(goal_for, fiscalyear_start_date, date_to, salesperson_ids)
        if goal_for == 'loss_no':
            oppo_target = self.get_planned_values('opportunity_no', fiscalyear_start_date, date_to, salesperson_ids)
            won_target = self.get_planned_values('won_no', fiscalyear_start_date, date_to, salesperson_ids)
            target = (oppo_target - won_target) > 0 and (oppo_target - won_target) or 0

        year_opportunities = self.env['crm.lead'].search(domain + stage_clause + date_clause3)
        year_opportunities_count = year_opportunities and len(year_opportunities) or 0

        opportunity_no.append(year_opportunities_count)
        opportunity_no.append(target)
        plan_y = target and (year_opportunities_count) / target or 0
        opportunity_no.append(str(round(plan_y * 100, 2)) + '%')

        year_amount = 0
        yr_day_close = 0
        for x in year_opportunities:
            year_amount += x.expected_revenue
            yr_day_close += x.day_close

        yr_team_target = 0
        if goal_for == 'won_no':
            yr_team_target = self.get_planned_values('won_amount', fiscalyear_start_date, date_to, salesperson_ids)

            yr_closing_target = self.get_planned_values('avg_closing_date', fiscalyear_start_date, date_to,
                                                        salesperson_ids)
            yr__avg_days = year_opportunities_count and yr_day_close and yr_day_close / year_opportunities_count or 0
            avg_days_closed.append(str(round(yr__avg_days, 2)) + ' days')
            avg_days_closed.append(str(yr_closing_target) + ' days')
            yr_closing_plan = yr_closing_target and (yr__avg_days) / yr_closing_target or 0
            avg_days_closed.append(str(round(yr_closing_plan * 100, 2)))

        elif goal_for == 'loss_no':
            yr_team_target = self.get_planned_values('loss_amount', fiscalyear_start_date, date_to, salesperson_ids)

        opportunity_amount.append(year_amount)
        opportunity_amount.append(yr_team_target)
        yr_plan_amount = yr_team_target and (year_amount) / yr_team_target or 0
        opportunity_amount.append(str(round(yr_plan_amount * 100, 2)) + '%')

        last_year_opportunities = self.env['crm.lead'].search(domain + stage_clause + date_clause4)
        last_year_opportunities_count = last_year_opportunities and len(last_year_opportunities) or 0
        opportunity_no.append(last_year_opportunities_count)
        inc_dec_y = last_year_opportunities_count and (
                float(year_opportunities_count) - float(last_year_opportunities_count)) / float(
            last_year_opportunities_count) or 0
        opportunity_no.append(str(round(inc_dec_y * 100, 2)) + '%')

        last_yr_amount = 0
        last_yr_day_close = 0
        for x in last_year_opportunities:
            last_yr_amount += x.expected_revenue
            last_yr_day_close += x.day_close

        opportunity_amount.append(last_yr_amount)
        yr_inc_dec_amount = last_yr_amount and (year_amount - last_yr_amount) / last_yr_amount or 0
        opportunity_amount.append(str(round(yr_inc_dec_amount * 100, 2)) + '%')

        if goal_for == 'won_no':
            last_yr_avg_days = last_yr_mnth_opportunities_count and last_yr_day_close and (
                    last_yr_day_close / last_yr_mnth_opportunities_count) or 0
            avg_days_closed.append(str(round(last_yr_avg_days, 2)) + ' days')
            yr_inc_dec_avg_days = last_yr_avg_days and (yr__avg_days - last_yr_avg_days) / last_yr_avg_days or 0
            avg_days_closed.append(str(round(yr_inc_dec_avg_days * 100, 2)))

        lly_opportunities = self.env['crm.lead'].search(domain + date_clause5 + stage_clause)
        llyear_opportunities_count = lly_opportunities and len(lly_opportunities) or 0

        lly_target = self.get_planned_values(goal_for, llyr_date_from, llyr_date_to, salesperson_ids)
        if goal_for == 'loss_no':
            oppo_target = self.get_planned_values('opportunity_no', llyr_date_from, llyr_date_to, salesperson_ids)
            won_target = self.get_planned_values('won_no', llyr_date_from, llyr_date_to, salesperson_ids)
            target = (oppo_target - won_target) > 0 and (oppo_target - won_target) or 0
        inc_dec_ly = llyear_opportunities_count and (
                float(last_year_opportunities_count) - float(llyear_opportunities_count)) / float(
            llyear_opportunities_count) or 0
        opportunity_no.append(llyear_opportunities_count)
        opportunity_no.append(str(round(inc_dec_ly * 100, 2)) + '%')

        llyear_amount = 0
        llyr_day_close = 0
        for x in lly_opportunities:
            llyear_amount += x.expected_revenue
            llyr_day_close += x.day_close

        llyr_team_target = 0
        if goal_for == 'won_no':
            llyr_team_target = self.get_planned_values('won_amount', llyr_date_from, llyr_date_to, salesperson_ids)

            llyr_closing_target = self.get_planned_values('avg_closing_date', llyr_date_from, llyr_date_to,
                                                          salesperson_ids)
            llyr__avg_days = llyear_opportunities_count and llyr_day_close and llyr_day_close / llyear_opportunities_count or 0
            ly_yr_inc_dec_avg_days = llyr__avg_days and (last_yr_avg_days - llyr__avg_days) / llyr__avg_days or 0
            avg_days_closed.append(str(round(llyr__avg_days, 2)) + ' days')
            avg_days_closed.append(str(round(ly_yr_inc_dec_avg_days * 100, 2)))

        elif goal_for == 'loss_no':
            llyr_team_target = self.get_planned_values('loss_amount', llyr_date_from, llyr_date_to, salesperson_ids)
        ly_yr_inc_dec_amount = llyear_amount and (last_yr_amount - llyear_amount) / llyear_amount or 0
        opportunity_amount.append(llyear_amount)
        opportunity_amount.append(str(round(ly_yr_inc_dec_amount * 100, 2)) + '%')
        return opportunity_no, opportunity_amount, avg_days_closed

    def get_closing_ratio(self, win_no, opportunity_no, month_start_date, date_to, last_yr_month_start_date,
                          last_yr_date_to, salesperson_ids):

        closing_ratio = ['Closing Ratio', 'perc']
        cr_mtd = opportunity_no[2] and win_no[2] / float(opportunity_no[2]) or 0
        closing_ratio.append(str(round(cr_mtd * 100, 2)) + '%')
        cr_target = self.get_planned_values('closing_ratio', month_start_date, date_to, salesperson_ids)
        cr_mplan = cr_target and (cr_mtd) / cr_target or 0
        closing_ratio.append(str(round(cr_target, 2)) + '%')
        closing_ratio.append(str(round(cr_mplan * 100, 2)) + '%')
        cr_lymtd = opportunity_no[5] and win_no[5] - float(opportunity_no[5]) or 0
        closing_ratio.append(str(round(cr_lymtd * 100, 2)) + '%')
        cr_minc_dec = cr_lymtd and (cr_mtd) / cr_lymtd or 0
        closing_ratio.append(str(round(cr_minc_dec * 100, 2)) + '%')
        cr_ytd = opportunity_no[7] and win_no[7] / float(opportunity_no[7]) or 0
        closing_ratio.append(str(round(cr_ytd * 100, 2)) + '%')
        cr_ytarget = self.get_planned_values('closing_ratio', last_yr_month_start_date, last_yr_date_to,
                                             salesperson_ids)
        closing_ratio.append(str(round(cr_ytarget, 2)) + '%')
        cr_yplan = cr_ytarget and (cr_ytd) / cr_ytarget or 0
        closing_ratio.append(str(round(cr_yplan * 100, 2)) + '%')

        cr_lytd = opportunity_no[10] and win_no[10] / float(opportunity_no[10]) or 0
        closing_ratio.append(str(round(cr_lytd * 100, 2)) + '%')
        cr_yinc_dec = cr_lytd and (cr_ytd - cr_lytd) or 0
        closing_ratio.append(str(round(cr_yinc_dec * 100, 2)) + '%')

        cr_llytd = opportunity_no[12] and win_no[12] / float(opportunity_no[12]) or 0
        closing_ratio.append(str(round(cr_llytd * 100, 2)) + '%')
        cr_lyinc_dec = cr_llytd and (cr_lytd - cr_llytd) or 0
        closing_ratio.append(str(round(cr_lyinc_dec * 100, 2)) + '%')
        return closing_ratio

    def get_crm_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                      fiscalyear_start_date,
                      last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from):
        lines = []
        opportunity_no = ['Opportunity #', 'count']
        opportunity_amount = ['Opportunity $', 'amount']
        win_no = ['Won #', 'count']
        win_amount = ['Won $', 'amount']
        lost_no = ['Lost #', 'count']
        lost_amount = ['Lost $', 'amount']

        context = self.env.context
        if 'options' in context:
            salesperson_ids = self.env['res.users'].browse(context['options']['users_ids'])
        else:
            salesperson_ids = context.get('users_ids', [])
        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])

        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids
            domain = [('type', '=', 'opportunity'), ('user_id', 'in', salesperson_ids)]
            clause1 = ['|', ('active', '=', False), ('active', '=', True)]
            clause2 = [('probability', '=', 100)]
            clause3 = [('probability', '=', 0), ('active', '=', False)]

            opportunity_no, opportunity_amount = self._get_stagewise_crm_lines('opportunity_no', salesperson_ids,
                                                                               opportunity_no, opportunity_amount,
                                                                               month_start_date, date_to,
                                                                               last_yr_month_start_date,
                                                                               last_yr_date_to,
                                                                               fiscalyear_start_date,
                                                                               last_yr_fiscalyear_start_date,
                                                                               domain,
                                                                               clause1, llyr_date_to,
                                                                               llyr_date_from)[
                                                 :2]
            win_no, win_amount, avg_days_closed = self._get_stagewise_crm_lines('won_no', salesperson_ids, win_no,
                                                                                win_amount, month_start_date,
                                                                                date_to,
                                                                                last_yr_month_start_date,
                                                                                last_yr_date_to,
                                                                                fiscalyear_start_date,
                                                                                last_yr_fiscalyear_start_date,
                                                                                domain,
                                                                                clause2, llyr_date_to,
                                                                                llyr_date_from)
            lost_no, lost_amount = self._get_stagewise_crm_lines('loss_no', salesperson_ids, lost_no, lost_amount,
                                                                 month_start_date, date_to,
                                                                 last_yr_month_start_date, last_yr_date_to,
                                                                 fiscalyear_start_date,
                                                                 last_yr_fiscalyear_start_date,
                                                                 domain, clause3, llyr_date_to, llyr_date_from)[:2]
            lines.append(opportunity_no)
            lines.append(opportunity_amount)
            lines.append(win_no)
            lines.append(win_amount)
            lines.append(lost_no)
            lines.append(lost_amount)

            closing_ratio = self.get_closing_ratio(win_no, opportunity_no, month_start_date, date_to,
                                                   last_yr_month_start_date, last_yr_date_to, salesperson_ids)
            lines.append(closing_ratio)
            lines.append(avg_days_closed)

        return lines

    def get_emails_sent_count(self, date_from, date_to, salesperson_ids):
        date_from = str(date_from)
        date_to = str(date_to)

        if date_from:
            date_from += ' 00:00:00'
        if date_to:
            date_to += ' 23:59:59'

        authors_ids = self.env['res.users'].browse(salesperson_ids)
        authors_ids_list = []
        for aut in authors_ids:
            authors_ids_list.append(aut.partner_id.id)

        salesperson_ids_str = ','.join(str(x) for x in authors_ids_list)
        salesperson_ids = '(' + salesperson_ids_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        sql = '''
            SELECT  COUNT(message.id) as total_message
            FROM mail_message message
            INNER JOIN res_partner partner on (partner.id = message.res_id)
            WHERE partner.customer_rank > 0 and message.message_type = 'comment' 
            and message.create_date >= '%s' 
            and message.create_date <= '%s' 
            and message.author_id in %s;
            ''' % (date_from, date_to, salesperson_ids)

        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res[0].get('total_message')

    def calculate_emails_filled(self, date_from, date_to, salesperson_ids):
        date_from = str(date_from)
        date_to = str(date_to)

        if date_from:
            date_from += ' 00:00:00'
        if date_to:
            date_to += ' 23:59:59'

        salesperson_ids_str = ','.join(str(x) for x in salesperson_ids)
        salesperson_ids = '(' + salesperson_ids_str + ')'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        sql = '''SELECT count (DISTINCT message.res_id) as total_changes from mail_tracking_value track
                    INNER JOIN mail_message message on (message.id = track.mail_message_id) 
                    INNER JOIN res_partner partner on (partner.id = message.res_id)
                    where track.field = 'email' and partner.customer_rank > 0 and partner.user_id in %s 
                    and track.create_date >='%s'  and track.create_date <='%s' ;''' % (
            salesperson_ids, date_from, date_to)

        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res[0].get('total_changes')

    def calculate_contact_card_completion(self, date_from, salesperson_ids):

        date_from = str(date_from)

        if date_from:
            date_from += ' 00:00:00'

        total_cards_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', date_from)])
        all_cards_completion_perc = self.env['res.partner'].search(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', date_from)])

        total_card_comp = 0
        for card in all_cards_completion_perc:
            total_card_comp += card.completion_perc

        if total_cards_count > 0:
            return total_card_comp / total_cards_count
        else:
            return 0

    def contact_activity_list(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                              fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from):
        list = []
        context = self.env.context
        if 'options' in context:
            salesperson_ids = self.env['res.users'].browse(context['options']['users_ids'])
        else:
            salesperson_ids = context.get('users_ids', [])

        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        new_contacts = ['New Contacts', 'count']
        new_contacts_target = self.get_planned_values('new_contacts', month_start_date, date_to, salesperson_ids)
        ytd_new_contacts_target = self.get_planned_values('new_contacts', fiscalyear_start_date, date_to,
                                                          salesperson_ids)
        new_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '>=', month_start_date),
             ('create_date', '<=', date_to)])
        ly_new_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '>=', last_yr_month_start_date), ('create_date', '<=', last_yr_date_to)])
        ytd_new_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '>=', fiscalyear_start_date), ('create_date', '<=', date_to)])
        lytd_new_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '>=', last_yr_fiscalyear_start_date), ('create_date', '<=', date_to)])

        llytd_new_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '>=', llyr_date_from), ('create_date', '<=', llyr_date_to)])

        llytd_new_contacts_target = self.get_planned_values('new_contacts', llyr_date_from, llyr_date_to,
                                                            salesperson_ids)
        new_contacts_inc_dec = ly_new_contacts_count and (
                new_contacts_count - ly_new_contacts_count) / ly_new_contacts_count or 0
        lytd_new_contacts_inc_dec = lytd_new_contacts_count and (
                ytd_new_contacts_count - lytd_new_contacts_count) / lytd_new_contacts_count or 0
        llytd_new_contacts_inc_dec = llytd_new_contacts_count and (
                lytd_new_contacts_count - llytd_new_contacts_count) / llytd_new_contacts_count or 0

        new_contacts.append(new_contacts_count)
        # new_contacts.append(new_contacts_target)
        new_contacts.append('')
        if new_contacts_target != 0.0:
            new_contacts.append(str(round(new_contacts_count / new_contacts_target * 100, 2)) + '%')
        else:
            new_contacts.append('')

        new_contacts.append(ly_new_contacts_count)
        new_contacts.append(str(round(new_contacts_inc_dec * 100, 2)) + '%')
        new_contacts.append(ytd_new_contacts_count)
        new_contacts.append(ytd_new_contacts_target)
        if ytd_new_contacts_target != 0.0:
            new_contacts.append(str(round(ytd_new_contacts_count / ytd_new_contacts_target * 100, 2)) + '%')
        else:
            new_contacts.append('')

        new_contacts.append(lytd_new_contacts_count)
        new_contacts.append(str(round(lytd_new_contacts_inc_dec * 100, 2)) + '%')

        new_contacts.append(llytd_new_contacts_count)
        new_contacts.append(str(round(llytd_new_contacts_inc_dec * 100, 2)) + '%')

        contacts_calls = ['Calls', 'count']
        calls_target = self.get_planned_values('calls_no', month_start_date, date_to, salesperson_ids)
        ytd_calls_target = self.get_planned_values('calls_no', fiscalyear_start_date, date_to, salesperson_ids)
        # ('phonecall_type', '=', 'outgoing'), Not available in version 16
        calls_count = self.env['voip.phonecall'].search_count(
            [('state', '=', 'done'), ('user_id', 'in', salesperson_ids),
             ('call_date', '>=', month_start_date), ('call_date', '<=', date_to)])
        # ('phonecall_type', '=', 'outgoing'), Not available in version 16
        ly_calls_count = self.env['voip.phonecall'].search_count(
            [('state', '=', 'done'), ('user_id', 'in', salesperson_ids),
             ('call_date', '>=', last_yr_month_start_date), ('call_date', '<=', last_yr_date_to)])
        # ('phonecall_type', '=', 'outgoing'), Not available in version 16
        ytd_calls_count = self.env['voip.phonecall'].search_count(
            [('state', '=', 'done'), ('user_id', 'in', salesperson_ids),
             ('call_date', '>=', fiscalyear_start_date), ('call_date', '<=', date_to)])
        # ('phonecall_type', '=', 'outgoing'), Not available in version 16
        lytd_calls_count = self.env['voip.phonecall'].search_count(
            [('state', '=', 'done'), ('user_id', 'in', salesperson_ids),
             ('call_date', '>=', last_yr_fiscalyear_start_date), ('call_date', '<=', date_to)])
        calls_inc_dec = ly_calls_count and (calls_count - ly_calls_count) / ly_calls_count or 0
        lytd_calls_inc_dec = lytd_calls_count and (ytd_calls_count - lytd_calls_count) / lytd_calls_count or 0
        # ('phonecall_type', '=', 'outgoing'), Not available in version 16
        llytd_calls_count = self.env['voip.phonecall'].search_count(
            [('state', '=', 'done'), ('user_id', 'in', salesperson_ids),
             ('call_date', '>=', llyr_date_from), ('call_date', '<=', llyr_date_to)])

        llytd_calls_target = self.get_planned_values('calls_no', llyr_date_from, llyr_date_to, salesperson_ids)
        llytd_calls_inc_dec = llytd_calls_count and (lytd_calls_count - llytd_calls_count) / llytd_calls_count or 0
        contacts_calls.append(calls_count)
        contacts_calls.append('')
        if calls_target != 0.0:
            contacts_calls.append(str(round(calls_count / calls_target * 100, 2)) + '%')
        else:
            contacts_calls.append('')
        contacts_calls.append(ly_calls_count)
        contacts_calls.append(str(round(calls_inc_dec * 100, 2)) + '%')
        contacts_calls.append(ytd_calls_count)
        contacts_calls.append(ytd_calls_target)
        if ytd_calls_target != 0.0:
            contacts_calls.append(str(round(ytd_calls_count / ytd_calls_target * 100, 2)) + '%')
        else:
            contacts_calls.append('')
        contacts_calls.append(lytd_calls_count)
        contacts_calls.append(str(round(lytd_calls_inc_dec * 100, 2)) + '%')

        contacts_calls.append(llytd_calls_count)
        contacts_calls.append(str(round(llytd_calls_inc_dec * 100, 2)) + '%')

        emails_sent = ['Emails', 'count']
        emails_target = self.get_planned_values('emails_no', month_start_date, date_to, salesperson_ids)
        ytd_emails_target = self.get_planned_values('emails_no', fiscalyear_start_date, date_to, salesperson_ids)
        emails_count = self.get_emails_sent_count(month_start_date, date_to, salesperson_ids)
        ly_emails_count = self.get_emails_sent_count(last_yr_month_start_date, last_yr_date_to, salesperson_ids)
        ytd_emails_count = self.get_emails_sent_count(fiscalyear_start_date, date_to, salesperson_ids)
        lytd_emails_count = self.get_emails_sent_count(last_yr_fiscalyear_start_date, date_to, salesperson_ids)
        emails_inc_dec = ly_emails_count and (emails_count - ly_emails_count) / ly_emails_count or 0
        lytd_emails_inc_dec = lytd_emails_count and (ytd_emails_count - lytd_emails_count) / lytd_emails_count or 0

        llytd_emails_count = self.get_emails_sent_count(llyr_date_from, llyr_date_to, salesperson_ids)
        llytd_emails_target = self.get_planned_values('emails_no', llyr_date_from, llyr_date_to, salesperson_ids)
        llytd_emails_inc_dec = llytd_emails_count and (lytd_emails_count - llytd_emails_count) / llytd_emails_count or 0
        emails_sent.append(emails_count)
        emails_sent.append('')
        if emails_target != 0.0:
            emails_sent.append(str(round(emails_count / emails_target * 100, 2)) + '%')
        else:
            emails_sent.append('')

        emails_sent.append(ly_emails_count)
        emails_sent.append(str(round(emails_inc_dec * 100, 2)) + '%')
        emails_sent.append(ytd_emails_count)
        emails_sent.append(ytd_emails_target)
        if ytd_emails_target != 0.0:
            emails_sent.append(str(round(ytd_emails_count / ytd_emails_target * 100, 2)) + '%')
        else:
            emails_sent.append('')
        emails_sent.append(lytd_emails_count)
        emails_sent.append(str(round(lytd_emails_inc_dec * 100, 2)) + '%')

        emails_sent.append(llytd_emails_count)
        emails_sent.append(str(round(llytd_emails_inc_dec * 100, 2)) + '%')

        sms_sent = ['SMS/MMS', 'count']
        sms_target = self.get_planned_values('sms_no', month_start_date, date_to, salesperson_ids)
        ytd_sms_target = self.get_planned_values('sms_no', fiscalyear_start_date, date_to, salesperson_ids)
        sms_count = self.env['mailing.mailing'].search_count(
            [('state', '=', 'done'), ('mailing_type', '=', 'sms'), ('user_id', 'in', salesperson_ids),
             ('sent_date', '>=', month_start_date), ('sent_date', '<=', date_to)])
        ly_sms_count = self.env['mailing.mailing'].search_count(
            [('state', '=', 'done'), ('mailing_type', '=', 'sms'), ('user_id', 'in', salesperson_ids),
             ('sent_date', '>=', last_yr_month_start_date), ('sent_date', '<=', last_yr_date_to)])
        ytd_sms_count = self.env['mailing.mailing'].search_count(
            [('state', '=', 'done'), ('mailing_type', '=', 'sms'), ('user_id', 'in', salesperson_ids),
             ('sent_date', '>=', fiscalyear_start_date), ('sent_date', '<=', date_to)])
        lytd_sms_count = self.env['mailing.mailing'].search_count(
            [('state', '=', 'done'), ('mailing_type', '=', 'sms'), ('user_id', 'in', salesperson_ids),
             ('sent_date', '>=', last_yr_fiscalyear_start_date), ('sent_date', '<=', date_to)])
        sms_inc_dec = ly_sms_count and (sms_count - ly_sms_count) / ly_sms_count or 0
        lytd_sms_inc_dec = lytd_sms_count and (ytd_sms_count - lytd_sms_count) / lytd_sms_count or 0

        llytd_sms_count = self.env['mailing.mailing'].search_count(
            [('state', '=', 'done'), ('mailing_type', '=', 'sms'), ('user_id', 'in', salesperson_ids),
             ('sent_date', '>=', llyr_date_from), ('sent_date', '<=', llyr_date_to)])

        llytd_sms_target = self.get_planned_values('sms_no', llyr_date_from, llyr_date_to, salesperson_ids)
        llytd_sms_inc_dec = llytd_sms_count and (lytd_sms_count - llytd_sms_count) / llytd_sms_count or 0

        sms_sent.append(sms_count)
        sms_sent.append('')
        if sms_target != 0.0:
            sms_sent.append(str(round(sms_count / sms_target * 100, 2)) + '%')
        else:
            sms_sent.append('')
        sms_sent.append(ly_sms_count)
        sms_sent.append(str(round(sms_inc_dec * 100, 2)) + '%')
        sms_sent.append(ytd_sms_count)
        sms_sent.append(ytd_sms_target)
        if ytd_sms_target != 0.0:
            sms_sent.append(str(round(ytd_sms_count / ytd_sms_target * 100, 2)) + '%')
        else:
            sms_sent.append('')
        sms_sent.append(lytd_sms_count)
        sms_sent.append(str(round(lytd_sms_inc_dec * 100, 2)) + '%')

        sms_sent.append(llytd_sms_count)
        sms_sent.append(str(round(llytd_sms_inc_dec * 100, 2)) + '%')

        contact_card_completion = ['Contact Card Completion %', 'perc']

        card_target = self.get_planned_values('contact_card_completion', month_start_date, date_to, salesperson_ids)
        ytd_card_target = self.get_planned_values('contact_card_completion', fiscalyear_start_date, date_to,
                                                  salesperson_ids)

        card_count = self.calculate_contact_card_completion(month_start_date, salesperson_ids)
        ly_card_count = self.calculate_contact_card_completion(last_yr_month_start_date, salesperson_ids)
        ytd_card_count = self.calculate_contact_card_completion(fiscalyear_start_date, salesperson_ids)
        lytd_card_count = self.calculate_contact_card_completion(last_yr_fiscalyear_start_date, salesperson_ids)

        card_inc_dec = card_count - ly_card_count
        lytd_card_inc_dec = ytd_card_count - lytd_card_count

        llytd_card_count = self.calculate_contact_card_completion(llyr_date_from, salesperson_ids)
        llytd_card_target = self.get_planned_values('contact_card', llyr_date_from, llyr_date_to, salesperson_ids)
        llytd_card_inc_dec = lytd_card_count - llytd_card_count

        contact_card_completion.append(str(card_count) + '%')
        contact_card_completion.append(str(card_target) + '%')
        contact_card_completion.append(str(card_count - card_target) + '%')

        contact_card_completion.append(str(ly_card_count) + '%')
        contact_card_completion.append(str(round(card_inc_dec, 2)) + '%')
        contact_card_completion.append(str(ytd_card_count) + '%')
        contact_card_completion.append(str(ytd_card_target) + '%')
        contact_card_completion.append(str(ytd_card_count - ytd_card_target) + '%')

        contact_card_completion.append(str(lytd_card_count) + '%')
        contact_card_completion.append(str(round(lytd_card_inc_dec, 2)) + '%')

        contact_card_completion.append(str(llytd_card_count) + '%')
        contact_card_completion.append(str(round(llytd_card_inc_dec, 2)) + '%')

        total_contacts = ['Total Contacts', 'count']

        ptd_total_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', date_to)])
        ly_total_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', last_yr_date_to)])
        ytd_total_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', fiscalyear_start_date)])
        lytd_total_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', last_yr_fiscalyear_start_date)])

        total_contacts_inc_dec = ly_total_contacts_count and (
                ptd_total_contacts_count - ly_total_contacts_count) / ly_total_contacts_count or 0
        lytd_new_contacts_inc_dec = lytd_total_contacts_count and (
                ytd_total_contacts_count - lytd_total_contacts_count) / lytd_total_contacts_count or 0

        llytd_total_contacts_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', llyr_date_from)])
        llytd_new_contacts_inc_dec = llytd_total_contacts_count and (
                lytd_total_contacts_count - llytd_total_contacts_count) / llytd_total_contacts_count or 0

        total_contacts.append(ptd_total_contacts_count)
        total_contacts.append('')
        total_contacts.append('0.00')
        total_contacts.append(ly_total_contacts_count)
        total_contacts.append(str(round(total_contacts_inc_dec * 100, 2)) + '%')
        total_contacts.append(ytd_total_contacts_count)
        total_contacts.append('0.00')
        total_contacts.append('0.00')
        total_contacts.append(lytd_total_contacts_count)
        total_contacts.append(str(round(lytd_new_contacts_inc_dec * 100, 2)) + '%')
        total_contacts.append(llytd_total_contacts_count)
        total_contacts.append(str(round(llytd_new_contacts_inc_dec * 100, 2)) + '%')

        birthdays = ['Birthdays %', 'perc']

        birthdays_target = self.get_planned_values('birthday_percentage', month_start_date, date_to, salesperson_ids)
        ytd_birthdays_target = self.get_planned_values('birthday_percentage', fiscalyear_start_date, date_to,
                                                       salesperson_ids)

        ptd_birthdays_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', date_to),
             ('birthday_month', '!=', None or False)])

        if ptd_birthdays_count > 0:
            ptd_birthdays_count = round((ptd_birthdays_count) / (ptd_total_contacts_count) * 100, 2)
        else:
            ptd_birthdays_count = 0

        ly_birthdays_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', last_yr_date_to),
             ('birthday_month', '!=', None or False)])
        if ly_birthdays_count > 0:
            ly_birthdays_count = round((ly_birthdays_count) / (ly_total_contacts_count) * 100, 2)
        else:
            ly_birthdays_count = 0

        ytd_birthdays_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', fiscalyear_start_date), ('birthday_month', '!=', None or False)])
        if ytd_birthdays_count > 0:
            ytd_birthdays_count = round((ytd_birthdays_count) / (ytd_total_contacts_count) * 100, 2)
        else:
            ytd_birthdays_count = 0

        lytd_birthdays_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', last_yr_fiscalyear_start_date), ('birthday_month', '!=', None or False)])

        if lytd_birthdays_count > 0:
            lytd_birthdays_count = round((lytd_birthdays_count) / (lytd_total_contacts_count) * 100, 2)
        else:
            lytd_birthdays_count = 0

        birthdays_inc_dec = ptd_birthdays_count - ly_birthdays_count
        lytd_birthdays_inc_dec = ytd_birthdays_count - lytd_birthdays_count

        llytd_birthdays_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', llyr_date_from), ('birthday_month', '!=', None or False)])
        if llytd_birthdays_count > 0:
            llytd_birthdays_count = round((llytd_birthdays_count) / (llytd_total_contacts_count) * 100, 2)
        else:
            llytd_birthdays_count = 0

        llytd_birthdays_inc_dec = lytd_birthdays_count - llytd_birthdays_count

        birthdays.append(str(ptd_birthdays_count) + '%')
        birthdays.append(str(birthdays_target) + '%')
        birthdays.append(str(ptd_birthdays_count - birthdays_target) + '%')
        birthdays.append(str(ly_birthdays_count) + '%')
        birthdays.append(str(round(birthdays_inc_dec, 2)) + '%')
        birthdays.append(str(ytd_birthdays_count) + '%')
        birthdays.append(str(ytd_birthdays_target) + '%')
        birthdays.append(str(ytd_birthdays_count - ytd_birthdays_target) + '%')
        birthdays.append(str(lytd_birthdays_count) + '%')
        birthdays.append(str(round(lytd_birthdays_inc_dec, 2)) + '%')
        birthdays.append(str(llytd_birthdays_count) + '%')
        birthdays.append(str(round(llytd_birthdays_inc_dec, 2)) + '%')

        emails_filled = ['Email Address %', 'perc']

        emails_filled_target = self.get_planned_values('email_address_percentage', month_start_date, date_to,
                                                       salesperson_ids)
        ytd_emails_filled_target = self.get_planned_values('email_address_percentage', fiscalyear_start_date, date_to,
                                                           salesperson_ids)

        ptd_emails_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', date_to),
             ('email', '!=', None or False)])
        if ptd_emails_count > 0:
            ptd_emails_count = round((ptd_emails_count) / (ptd_total_contacts_count) * 100, 2) or 0
        else:
            ptd_emails_count = 0

        ly_emails_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids), ('create_date', '<=', last_yr_date_to),
             ('email', '!=', None or False)])
        if ly_emails_count > 0:
            ly_emails_count = round((ly_emails_count) / (ly_total_contacts_count) * 100, 2)
        else:
            ly_emails_count = 0

        ytd_emails_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', fiscalyear_start_date), ('email', '!=', None or False)])
        if ytd_emails_count > 0:
            ytd_emails_count = round((ytd_emails_count) / (ytd_total_contacts_count) * 100, 2)
        else:
            ytd_emails_count = 0

        lytd_emails_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', last_yr_fiscalyear_start_date), ('email', '!=', None or False)])
        if ly_emails_count > 0:
            lytd_emails_count = round((lytd_emails_count) / (lytd_total_contacts_count) * 100, 2)
        else:
            lytd_emails_count = 0

        emails_inc_dec = ptd_emails_count - ly_emails_count
        lytd_emails_inc_dec = ytd_emails_count - lytd_emails_count

        llytd_emails_count = self.env['res.partner'].search_count(
            [('customer_rank', '>', 0), ('user_id', 'in', salesperson_ids),
             ('create_date', '<=', llyr_date_from), ('email', '!=', None or False)])
        if llytd_emails_count > 0:
            llytd_emails_count = round((llytd_emails_count) / (llytd_total_contacts_count) * 100, 2)
        else:
            llytd_emails_count = 0

        llytd_emails_inc_dec = lytd_emails_count - llytd_emails_count
        emails_filled.append(str(ptd_emails_count) + '%')
        emails_filled.append(str(emails_filled_target) + '%')
        emails_filled.append(str(ptd_emails_count - emails_filled_target) + '%')

        emails_filled.append(str(ly_emails_count) + '%')
        emails_filled.append(str(round(emails_inc_dec, 2)) + '%')
        emails_filled.append(str(ytd_emails_count) + '%')
        emails_filled.append(str(ytd_emails_filled_target) + '%')
        emails_filled.append(str(ytd_emails_count - ytd_emails_filled_target) + '%')
        emails_filled.append(str(lytd_emails_count) + '%')
        emails_filled.append(str(round(lytd_emails_inc_dec, 2)) + '%')
        emails_filled.append(str(llytd_emails_count) + '%')
        emails_filled.append(str(round(llytd_emails_inc_dec, 2)) + '%')

        list.append(contacts_calls)
        list.append(sms_sent)
        list.append(emails_sent)
        list.append(new_contacts)
        list.append(total_contacts)
        list.append(birthdays)
        list.append(emails_filled)
        list.append(contact_card_completion)

        return list

    def get_bonus_potential_based_on_perc(self, percentage, gross_margin_list):
        lines = []
        mnth_bp_amount = gross_margin_list[2] * percentage
        mnth_bp_target = gross_margin_list[3] * percentage
        mnth_bp_plan = mnth_bp_target and (mnth_bp_amount) / mnth_bp_target or 0
        ly_mnth_bp_amount = gross_margin_list[6] * percentage
        mnth_bp_inc_dec = ly_mnth_bp_amount and (mnth_bp_amount - ly_mnth_bp_amount) / ly_mnth_bp_amount or 0
        yr_bp_amount = gross_margin_list[8] * percentage
        yr_bp_target = gross_margin_list[9] * percentage
        yr_bp_plan = yr_bp_target and (yr_bp_amount) / yr_bp_target or 0
        ly_yr_bp_amount = gross_margin_list[11] * percentage
        yr_bp_inc_dec = ly_yr_bp_amount and (yr_bp_amount - ly_yr_bp_amount) / ly_yr_bp_amount or 0

        lines.append(round(mnth_bp_amount, 2))
        lines.append(round(mnth_bp_target, 2))
        lines.append(str(round(mnth_bp_plan * 100, 2)) + '%')
        lines.append(round(mnth_bp_amount - mnth_bp_target, 2))
        lines.append(round(ly_mnth_bp_amount, 2))
        lines.append(str(round(mnth_bp_inc_dec * 100, 2)) + '%')
        lines.append(round(yr_bp_amount, 2))
        lines.append(round(yr_bp_target, 2))
        lines.append(str(round(yr_bp_plan * 100, 2)) + '%')
        lines.append(round(ly_yr_bp_amount, 2))
        lines.append(str(round(yr_bp_inc_dec * 100, 2)) + '%')
        return lines

    def get_saleperson_based_commission(self, date_params, salesperson_id):
        month_start_date, date_to, last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from = date_params
        net_sale_list = []
        gross_margin_list = []
        result_list = self.with_context(users_ids=salesperson_id).get_sale_lines(month_start_date, date_to,
            last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date, last_yr_fiscalyear_start_date,
            llyr_date_to, llyr_date_from)

        for values in result_list:
            if values[0] not in ('Retail', 'Discount $', 'Discount %'):
                if values[0] == 'Net Sale':
                    net_sale_list = values
                if values[0] == 'Gross Margin $':
                    gross_margin_list = values

        result_list = self.with_context(users_ids=salesperson_id).get_repair_service_lines('Repairs', 'repair',
            month_start_date, date_to, last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
            last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from)
        repairs_gross_margin = result_list[1][2]
        repairs_gross_plan = result_list[1][3]
        ly_repairs_gross_margin = result_list[1][5]
        ytd_repairs_gross_margin = result_list[1][7]
        lytd_repairs_gross_margin = result_list[1][10]

        result_list = self.with_context(users_ids=salesperson_id).get_repair_service_lines('Services', 'service',
           month_start_date, date_to, last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
           last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from)

        services_gross_margin = result_list[1][2]
        services_gross_plan = result_list[1][3]
        ly_services_gross_margin = result_list[1][5]
        ytd_services_gross_margin = result_list[1][7]
        lytd_services_gross_margin = result_list[1][10]

        gross_margin_list[2] = gross_margin_list[2] + repairs_gross_margin + services_gross_margin
        gross_margin_list[3] = gross_margin_list[3] + repairs_gross_plan + services_gross_plan
        gross_margin_list[5] = gross_margin_list[5] + ly_repairs_gross_margin + ly_services_gross_margin
        gross_margin_list[7] = gross_margin_list[7] + ytd_repairs_gross_margin + ytd_services_gross_margin
        gross_margin_list[10] = gross_margin_list[10] + lytd_repairs_gross_margin + lytd_services_gross_margin
        return gross_margin_list

    def get_bonus_potential_general(self, percentage, gross_margin_list, temp_list):
        mnth_bp_amount = gross_margin_list[2] * percentage
        mnth_bp_target = gross_margin_list[3] * percentage
        mnth_bp_plan = mnth_bp_target and (mnth_bp_amount) / mnth_bp_target or 0
        ly_mnth_bp_amount = gross_margin_list[5] * percentage
        mnth_bp_inc_dec = ly_mnth_bp_amount and (mnth_bp_amount - ly_mnth_bp_amount) / ly_mnth_bp_amount or 0
        yr_bp_amount = gross_margin_list[7] * percentage
        yr_bp_target = gross_margin_list[8] * percentage
        yr_bp_plan = yr_bp_target and (yr_bp_amount) / yr_bp_target or 0
        ly_yr_bp_amount = gross_margin_list[10] * percentage
        yr_bp_inc_dec = ly_yr_bp_amount and (yr_bp_amount - ly_yr_bp_amount) / ly_yr_bp_amount or 0
        llyr_bp_amount = gross_margin_list[12] * percentage
        llyr_bp_inc_dec = llyr_bp_amount and (ly_yr_bp_amount - llyr_bp_amount) / llyr_bp_amount or 0
        temp = [mnth_bp_amount, mnth_bp_target, mnth_bp_plan, ly_mnth_bp_amount, mnth_bp_inc_dec, yr_bp_amount,
                yr_bp_target, yr_bp_plan, ly_yr_bp_amount, yr_bp_inc_dec, llyr_bp_amount, llyr_bp_inc_dec]
        if not temp_list:
            return temp
        return list(map(add, temp, temp_list))

    def get_bonus_potential_list(self, temp_list):
        lines = []
        (mnth_bp_amount, mnth_bp_target, mnth_bp_plan, ly_mnth_bp_amount, mnth_bp_inc_dec, yr_bp_amount, yr_bp_target,
         yr_bp_plan, ly_yr_bp_amount, yr_bp_inc_dec, llyr_bp_amount, llyr_bp_inc_dec) = temp_list

        lines.append(round(mnth_bp_amount, 2))
        lines.append(round(mnth_bp_amount - mnth_bp_target, 2))
        lines.append(str(round(mnth_bp_plan * 100, 2)) + '%')
        lines.append(round(ly_mnth_bp_amount, 2))
        lines.append(str(round(mnth_bp_inc_dec * 100, 2)) + '%')
        lines.append(round(yr_bp_amount, 2))
        lines.append(round(yr_bp_target, 2))
        lines.append(str(round(yr_bp_plan * 100, 2)) + '%')
        lines.append(round(ly_yr_bp_amount, 2))
        lines.append(str(round(yr_bp_inc_dec * 100, 2)) + '%')
        lines.append(round(llyr_bp_amount, 2))
        lines.append(str(round(llyr_bp_inc_dec * 100, 2)) + '%')
        return lines

    def get_bonus_potential(self, gross_margin_list, date_params):
        minimum, goal, stretch = ['Base', 'amount'], ['Goal', 'amount'], ['Stretch', 'amount']
        base_list, goal_list, stretch_list = [], [], []
        salesperson_ids = self.env.context.get('users_ids', []) or self.env['res.users'].search(
            ['|', ('active', '=', False), ('active', '=', True)])
        for salesperson_id in salesperson_ids.filtered(lambda sp: sp.employee_id):
            gross_margin_list = self.get_saleperson_based_commission(date_params, salesperson_id)
            base_list = self.get_bonus_potential_general(salesperson_id.employee_id.base_percentage / 100,
                                                         gross_margin_list, base_list)
            goal_list = self.get_bonus_potential_general(salesperson_id.employee_id.goal_percentage / 100,
                                                         gross_margin_list, goal_list)
            stretch_list = self.get_bonus_potential_general(salesperson_id.employee_id.stretch_percentage / 100,
                                                            gross_margin_list, stretch_list)
        minimum += self.get_bonus_potential_list(base_list)
        goal += self.get_bonus_potential_list(goal_list)
        stretch += self.get_bonus_potential_list(stretch_list)
        lines = []
        lines.append(minimum)
        lines.append(goal)
        lines.append(stretch)
        return lines

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lines = []
        line_id = 0

        context = self.env.context
        company_id = context.get('company_id') or self.env.user.company_id

        date_to = context.get('date_to', False)
        if not date_to:
            if options.get('date'):
                date_to = options['date'].get('date_to') or options['date'].get('date')

        date_to_obj = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT).date()
        date_from = context.get('date_from', False)
        if not date_from:
            if options.get('date') and options['date'].get('date_from'):
                date_from = options['date']['date_from']
        date_from_obj = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT).date()
        month_start_date = date_from

        last_yr_date_to = date_to_obj - relativedelta(years=1)
        last_yr_date_from = date_from_obj - relativedelta(years=1)

        last_yr_month_start_date = last_yr_date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)

        fiscalyear_last_day = company_id.fiscalyear_last_day
        fiscalyear_last_month = company_id.fiscalyear_last_month

        fiscalyear_last_date = date_to_obj.replace(month=int(fiscalyear_last_month), day=int(fiscalyear_last_day))

        if fiscalyear_last_date < date_to_obj:
            fiscalyear_start_date = (fiscalyear_last_date + timedelta(days=1))
        else:
            fiscalyear_start_date = (fiscalyear_last_date + timedelta(days=1)) - relativedelta(years=+1)

        last_yr_fiscalyear_start_date = fiscalyear_start_date - relativedelta(years=1)

        llyr_date_to = date_to_obj - relativedelta(years=2)
        llyr_date_from = fiscalyear_start_date - relativedelta(years=2)

        salesperson_ids = context.get('users_ids', [])

        if not salesperson_ids:
            salesperson_ids = self.env['res.users'].search(['|', ('active', '=', False), ('active', '=', True)])
        if salesperson_ids:
            salesperson_ids = salesperson_ids.ids

        # Sales
        lines.append({
            'id': line_id,
            'name': 'Sales',
            'unfoldable': False,
            'type': 'line_solid',
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'title_hover': _('Vendor 1'),
            'level': 1,
        })
        line_id += 1

        net_sale_list = []
        gross_margin_list = []
        result_list = self.with_context({'options':options}).get_sale_lines(month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                                          fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                                          llyr_date_from)
        for values in result_list:
            if values[0] == 'Net Sale':
                net_sale_list = values
            if values[0] == 'Gross Margin $':
                gross_margin_list = values
            list = self.update_symbols(values)
            lines.append({
                'id': line_id,
                'name': values[0],
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1
        ####################################################

        # Transactions
        lines.append({
            'id': line_id,
            'name': 'Transactions',
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'level': 1,
        })
        line_id += 1
        result_list = self.with_context({'options':options}).get_transaction_lines(net_sale_list, month_start_date, date_to,
                                                 last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                                 last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from)
        for values in result_list:
            list = self.update_symbols(values)
            lines.append({
                'id': line_id,
                'name': values[0],
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1

        # Repairs
        lines.append({
            'id': line_id,
            'name': 'Repairs',
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'level': 1,
        })
        line_id += 1

        result_list = self.with_context({'options':options}).get_repair_service_lines('Repairs', 'repair', month_start_date, date_to,
                                                    last_yr_month_start_date, last_yr_date_to,
                                                    fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                                                    llyr_date_from)
        repairs_gross_margin = result_list[1][2]
        repairs_gross_plan = result_list[1][3]
        ly_repairs_gross_margin = result_list[1][5]
        ytd_repairs_gross_margin = result_list[1][7]
        lytd_repairs_gross_margin = result_list[1][10]

        for values in result_list:
            list = self.update_symbols(values)
            lines.append({
                'id': line_id,
                'name': values[0],
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1

        # Services
        lines.append({
            'id': line_id,
            'name': 'Services',
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'level': 1,
        })
        line_id += 1

        result_list = self.with_context({'options':options}).get_repair_service_lines('Services', 'service', month_start_date, date_to,
                                                    last_yr_month_start_date, last_yr_date_to,
                                                    fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                                                    llyr_date_from)
        services_gross_margin = result_list[1][2]
        services_gross_plan = result_list[1][3]
        ly_services_gross_margin = result_list[1][5]
        ytd_services_gross_margin = result_list[1][7]
        lytd_services_gross_margin = result_list[1][10]

        for values in result_list:
            list = self.update_symbols(values)
            lines.append({
                'id': line_id,
                'name': values[0],
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1

        # Commission(Based on Gross Margin)

        lines.append({
            'id': line_id,
            'name': 'Commission (Based on Gross Margin)',
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'level': 1,
        })
        line_id += 1

        gross_margin_list[2] = gross_margin_list[2] + repairs_gross_margin + services_gross_margin
        gross_margin_list[3] = gross_margin_list[3]
        gross_margin_list[5] = gross_margin_list[5] + ly_repairs_gross_margin + ly_services_gross_margin
        gross_margin_list[7] = gross_margin_list[7] + ytd_repairs_gross_margin + ytd_services_gross_margin
        gross_margin_list[10] = gross_margin_list[10] + lytd_repairs_gross_margin + lytd_services_gross_margin
        if gross_margin_list:
            date_params = [month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                           fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                           llyr_date_from]
            result_list = self.get_bonus_potential(gross_margin_list, date_params)
            # *****----------------- updates for commission based on individual user --------------*****
            for values in result_list:
                m_inc_dec = values[5] and (values[3] - values[5]) / values[5] or 0
                values[6] = str(round(m_inc_dec * 100, 2)) + '%'
                y_inc_dec = values[10] and (values[7] - values[10]) / values[10] or 0
                values[11] = str(round(y_inc_dec * 100, 2)) + '%'
                ly_inc_dec = values[12] and (values[10] - values[12]) / values[12] or 0
                values[13] = str(round(ly_inc_dec * 100, 2)) + '%'
            for values in result_list:
                list = self.update_symbols(values)
                lines.append({
                    'id': line_id,
                    'name': values[0],
                    'unfoldable': False,
                    'columns': list,
                    'level': 3,
                })
                line_id += 1

        # CRM
        lines.append({
            'id': line_id,
            'name': 'CRM',
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'level': 1,
        })
        line_id += 1

        result_list = self.with_context({'options':options}).get_crm_lines(month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                                         fiscalyear_start_date, last_yr_fiscalyear_start_date, llyr_date_to,
                                         llyr_date_from)
        for values in result_list:
            list = self.update_symbols(values)
            lines.append({
                'id': line_id,
                'name': values[0],
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1

        # Contact Activity
        lines.append({
            'id': line_id,
            'name': 'Contact Activity',
            'unfoldable': False,
            'class': 'o_account_reports_level1',
            'columns': [{'name': ''} for k in range(0, 11)],
            'level': 1,
        })
        line_id += 1
        contact_list = self.with_context({'options':options}).contact_activity_list(month_start_date, date_to, last_yr_month_start_date,
                                                  last_yr_date_to, fiscalyear_start_date,
                                                  last_yr_fiscalyear_start_date, llyr_date_to, llyr_date_from)
        for contacts in contact_list:
            list = self.update_symbols(contacts)
            lines.append({
                'id': line_id,
                'name': contacts[0],
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1
        return [(0, line) for line in lines]
