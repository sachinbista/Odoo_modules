# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from datetime import datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from six import string_types

from odoo import models, fields


class ClientHistoryReportHandler(models.AbstractModel):
    _name = 'client.history.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Client History Report Handler'

    def get_crm_details(self, date_from, date_to, customer_ids, stage):
        if date_from:
            date_from += ' 00:00:00'
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)

        sql = ("""
            SELECT 
                COUNT(cl.id) as count, 
                SUM(cl.expected_revenue) as expected_revenue, 
                SUM(cl.day_close) as day_close 
            FROM crm_lead cl 
                INNER JOIN crm_stage as cs on (cl.stage_id = cs.id)
            WHERE  
                cl.type ='opportunity' and
                cl.partner_id in %s and 
                cl.create_date >= '%s' and 
                cl.create_date <= '%s' 
        """) % (customer_ids, date_from, date_to)
        if stage == 'won':
            sql += ' and cl.probability = 100 and cl.active=True'
        elif stage == 'loss':
            sql += ' and (cl.probability = 0 or cl.active=False)'
        else:
            sql += ' and cl.probability != 100 and cl.active=True'

        self._cr.execute(sql)
        res = self._cr.dictfetchall()[0]
        return res.get('count', 0) or 0, res.get('expected_revenue', 0) or 0, res.get('day_close', 0) or 0

    def _get_stagewise_crm_lines(self, calculate_avg_days, opportunity_no, opportunity_amount, month_start_date,
                                 date_to, last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                 last_yr_fiscalyear_start_date, customer_ids, stage):

        avg_days_closed = ['Average Days to Close', 'count']
        mnth_opportunities_count, mnth_amount, day_close = self.get_crm_details(
            month_start_date, date_to, customer_ids, stage)
        opportunity_no.append(mnth_opportunities_count)

        if calculate_avg_days:
            mnth_avg_days = mnth_opportunities_count and day_close and day_close / mnth_opportunities_count or 0
            avg_days_closed.append(str(round(mnth_avg_days, 2)) + ' days')

        opportunity_amount.append(mnth_amount)

        last_yr_mnth_opportunities_count, last_yr_mnth_amount, last_yr_mnth_day_close = self.get_crm_details(
            str(last_yr_month_start_date), str(last_yr_date_to), customer_ids, stage)

        opportunity_no.append(last_yr_mnth_opportunities_count)
        inc_dec_m = last_yr_mnth_opportunities_count and (
                float(mnth_opportunities_count) - float(last_yr_mnth_opportunities_count)) / float(
            last_yr_mnth_opportunities_count) or 0
        opportunity_no.append(str(round(inc_dec_m * 100, 2)) + '%')

        last_yr_mnth_avg_days = 0

        if calculate_avg_days:
            last_yr_mnth_avg_days = last_yr_mnth_opportunities_count and last_yr_mnth_day_close and (
                    last_yr_mnth_day_close / last_yr_mnth_opportunities_count) or 0
            avg_days_closed.append(str(round(last_yr_mnth_avg_days, 2)) + ' days')
            m_inc_dec_avg_days = last_yr_mnth_avg_days and (
                    mnth_avg_days - last_yr_mnth_avg_days) / last_yr_mnth_avg_days or 0
            avg_days_closed.append(str(round(m_inc_dec_avg_days, 2)))

        opportunity_amount.append(last_yr_mnth_amount)
        m_inc_dec_amount = last_yr_mnth_amount and (mnth_amount - last_yr_mnth_amount) / last_yr_mnth_amount or 0
        opportunity_amount.append(str(round(m_inc_dec_amount * 100, 2)) + '%')

        year_opportunities_count, year_amount, yr_day_close = self.get_crm_details(str(fiscalyear_start_date), date_to,
                                                                                   customer_ids, stage)

        opportunity_no.append(year_opportunities_count)

        if calculate_avg_days:
            yr__avg_days = year_opportunities_count and yr_day_close and yr_day_close / year_opportunities_count or 0
            avg_days_closed.append(str(round(yr__avg_days, 2)) + ' days')

        opportunity_amount.append(year_amount)

        last_year_opportunities_count, last_yr_amount, last_yr_day_close = self.get_crm_details(
            str(last_yr_fiscalyear_start_date), str(last_yr_date_to), customer_ids, stage)
        opportunity_no.append(last_year_opportunities_count)
        inc_dec_y = last_year_opportunities_count and (
                float(year_opportunities_count) - float(last_year_opportunities_count)) / float(
            last_year_opportunities_count) or 0
        opportunity_no.append(str(round(inc_dec_y * 100, 2)) + '%')

        opportunity_amount.append(last_yr_amount)
        yr_inc_dec_amount = last_yr_amount and (year_amount - last_yr_amount) / last_yr_amount or 0
        opportunity_amount.append(str(round(yr_inc_dec_amount * 100, 2)) + '%')

        if calculate_avg_days:
            last_yr_avg_days = last_yr_mnth_opportunities_count and last_yr_day_close and (
                    last_yr_day_close / last_yr_mnth_opportunities_count) or 0
            avg_days_closed.append(str(round(last_yr_avg_days, 2)) + ' days')
            yr_inc_dec_avg_days = last_yr_avg_days and (yr__avg_days - last_yr_avg_days) / last_yr_avg_days or 0
            avg_days_closed.append(str(round(yr_inc_dec_avg_days, 2)))

        return opportunity_no, opportunity_amount, avg_days_closed

    def get_closing_ratio(self, win_no, opportunity_no):
        closing_ratio = ['Closing Ratio', 'perc']
        cr_mtd = opportunity_no[2] and win_no[2] / opportunity_no[2] or 0
        cr_lymtd = opportunity_no[3] and win_no[3] / opportunity_no[3] or 0
        cr_m_inc_dec = cr_lymtd and (cr_mtd - cr_lymtd) or 0
        cr_ytd = opportunity_no[5] and win_no[5] / opportunity_no[5] or 0
        cr_lytd = opportunity_no[6] and win_no[6] / opportunity_no[6] or 0
        cr_y_inc_dec = cr_lytd and (cr_ytd - cr_lytd) or 0
        closing_ratio.append(str(round(cr_mtd * 100, 2)) + '%')
        closing_ratio.append(str(round(cr_lymtd * 100, 2)) + '%')
        closing_ratio.append(str(round(cr_m_inc_dec * 100, 2)) + '%')
        closing_ratio.append(str(round(cr_ytd * 100, 2)) + '%')
        closing_ratio.append(str(round(cr_lytd * 100, 2)) + '%')
        closing_ratio.append(str(round(cr_y_inc_dec * 100, 2)) + '%')
        return closing_ratio
        # ===========================================================================

    # Function for add timezone with given date
    # ===========================================================================
    def get_date_with_tz(self, date):
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        datetime_with_tz = fields.Datetime.from_string(date).astimezone(timezone).date() 
        date = datetime_with_tz.strftime('%Y-%m-%d %H:%M:%S')
        return date

    def get_sale_amount(self, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date, customer_ids, sale_type='sale', check_delivery=None):
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
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)
        print("customer_ids",customer_ids)
        if check_delivery:
            sql = ("""
            select 
                sum(sm.product_uom_qty), 
                sum(case when pt.list_price = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' and pt.list_price = 0.0 then (sol.price_unit * sol.qty_delivered) when pt.type = 'service' and pt.list_price != 0.0 then (pt.list_price * sol.qty_delivered) else (pt.list_price * sm.product_uom_qty) end) as sale_price, 
                sum(case when sol.discount = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' then sol.price_subtotal else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end) as invoice_price, 
                sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price,
                sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as gross_margin
                ,0.0 as ly_mnth_retail_amount
                ,0.0 as ly_mnth_invoice_amount
                ,0.0 as ly_mnth_gross_amount
                ,0.0 as yr_retail_amount
                ,0.0 as yr_invoice_amount
                ,0.0 as yr_gross_amount
                ,0.0 as ly_yr_retail_amount
                ,0.0 as ly_yr_invoice_amount
                ,0.0 as ly_yr_gross_amount 
            from sale_order_line sol
                inner join stock_move sm on sm.sale_line_id = sol.id
                inner join stock_picking sp on sp.id=sm.picking_id
                inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
                inner join res_partner rp on (rp.id = sol.order_partner_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where sp.date_done >= '%s' 
                and sp.date_done <= '%s' 
                and sp.state = 'done' 
                and spt.code='outgoing' 
                and sm.product_id = sol.product_id
                and sm.state ='done' 
                and sol.order_partner_id in %s
                and pt.exclude_from_report !=True
                UNION ALL
                Select 
                sum(sm.product_uom_qty)
                ,0.0 as sale_price
                ,0.0 as invoice_price
                ,0.0 as gross_margin
                ,sum(case when pt.list_price = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' and pt.list_price = 0.0 then (sol.price_unit * sol.qty_delivered) when pt.type = 'service' and pt.list_price != 0.0 then (pt.list_price * sol.qty_delivered) else (pt.list_price * sm.product_uom_qty) end) as ly_mnth_retail_amount, 
                sum(case when sol.discount = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' then sol.price_subtotal else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end) as ly_mnth_invoice_amount, 
                sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price,
                sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_gross_amount
                ,0.0 as yr_retail_amount
                ,0.0 as yr_invoice_amount
                ,0.0 as yr_gross_amount
                ,0.0 as ly_yr_retail_amount
                ,0.0 as ly_yr_invoice_amount
                ,0.0 as ly_yr_gross_amount 
                from sale_order_line sol
                    inner join stock_move sm on sm.sale_line_id = sol.id
                    inner join stock_picking sp on sp.id=sm.picking_id
                    inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
                    inner join res_partner rp on (rp.id = sol.order_partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='outgoing' 
                    and sm.product_id = sol.product_id
                    and sm.state !='cancel' 
                    and sol.order_partner_id in %s
                    and pt.exclude_from_report !=True
                UNION ALL
                Select 
                 sum(sm.product_uom_qty)
                ,0.0 as sale_price
                ,0.0 as invoice_price
                ,0.0 as gross_margin 
                ,0.0 as ly_mnth_retail_amount
                ,0.0 as ly_mnth_invoice_amount
                ,0.0 as ly_mnth_gross_amount
                ,sum(case when pt.list_price = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' and pt.list_price = 0.0 then (sol.price_unit * sol.qty_delivered) when pt.type = 'service' and pt.list_price != 0.0 then (pt.list_price * sol.qty_delivered) else (pt.list_price * sm.product_uom_qty) end) as yr_retail_amount, 
                sum(case when sol.discount = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' then sol.price_subtotal else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end) as yr_invoice_amount, 
                sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price,
                sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_gross_amount
                ,0.0 as ly_yr_retail_amount
                ,0.0 as ly_yr_invoice_amount
                ,0.0 as ly_yr_gross_amount 
                from sale_order_line sol
                    inner join stock_move sm on sm.sale_line_id = sol.id
                    inner join stock_picking sp on sp.id=sm.picking_id
                    inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
                    inner join res_partner rp on (rp.id = sol.order_partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='outgoing' 
                    and sm.product_id = sol.product_id
                    and sm.state !='cancel' 
                    and sol.order_partner_id in %s
                    and pt.exclude_from_report !=True
                UNION ALL
                Select 
                sum(sm.product_uom_qty)
                ,0.0 as sale_price
                ,0.0 as invoice_price
                ,0.0 as gross_margin 
                ,0.0 as ly_mnth_retail_amount
                ,0.0 as ly_mnth_invoice_amount
                ,0.0 as ly_mnth_gross_amount
                ,0.0 as yr_retail_amount
                ,0.0 as yr_invoice_amount
                ,0.0 as yr_gross_amount,
                sum(case when pt.list_price = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' and pt.list_price = 0.0 then (sol.price_unit * sol.qty_delivered) when pt.type = 'service' and pt.list_price != 0.0 then (pt.list_price * sol.qty_delivered) else (pt.list_price * sm.product_uom_qty) end) as ly_yr_retail_amount, 
                sum(case when sol.discount = 0.0 and pt.type != 'service' then (sol.price_unit * sm.product_uom_qty) when pt.type = 'service' then sol.price_subtotal else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end) as ly_yr_invoice_amount, 
                sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as cost_price,
                sum(case when sol.discount = 0.0 then (sol.price_unit * sm.product_uom_qty) else ((sol.price_unit * sm.product_uom_qty) * (sol.discount)) / 100.0 end - case when pp.std_price = 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_gross_amount
                from sale_order_line sol
                    inner join stock_move sm on sm.sale_line_id = sol.id
                    inner join stock_picking sp on sp.id=sm.picking_id
                    inner join stock_picking_type spt on (spt.id = sm.picking_type_id)
                    inner join res_partner rp on (rp.id = sol.order_partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    inner join product_template pt on (pp.product_tmpl_id = pt.id)
                    inner join product_category pc on (pc.id = pt.categ_id) 
                where sp.date_done >= '%s' 
                    and sp.date_done <= '%s' 
                    and sp.state = 'done' 
                    and spt.code='outgoing' 
                    and sm.product_id = sol.product_id
                    and sm.state !='cancel' 
                    and sol.order_partner_id in %s
                    and pt.exclude_from_report !=True

            """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)
        
        else:
            sql = ("""
            select 
                sum(sol.product_uom_qty)
                ,sum(case when pt.list_price = 0.0 then (sol.price_unit*sol.product_uom_qty) else (pt.list_price* sol.product_uom_qty) end) as sale_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty) else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end) as invoice_price 
                ,sum(case when pp.std_price= 0.0 then 0  else (pp.std_price * sol.product_uom_qty) end) as cost_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty)  else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as gross_margin
                 ,0.0 as ly_mnth_retail_amount
                 ,0.0 as ly_mnth_invoice_amount
                 ,0.0 as ly_mnth_gross_amount
                 ,0.0 as yr_retail_amount
                 ,0.0 as yr_invoice_amount
                 ,0.0 as yr_gross_amount
                 ,0.0 as ly_yr_retail_amount
                 ,0.0 as ly_yr_invoice_amount
                 ,0.0 as ly_yr_gross_amount 
            from sale_order_line sol
                inner join res_partner rp on (rp.id = sol.order_partner_id)
                inner join sale_order so on (so.id = sol.order_id)
                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                inner join account_move ai on (ai.id = ail.move_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where ai.state in ('open','paid') and 
                so.date_order >= '%s' 
                and so.date_order <= '%s' 
                and sol.order_partner_id in %s 
                and pt.exclude_from_report !=True
            UNION ALL
            select 
                sum(sol.product_uom_qty)
                ,0.0 as sale_price
                ,0.0 as invoice_price
                ,0.0 as gross_margin
                ,sum(case when pt.list_price = 0.0 then (sol.price_unit*sol.product_uom_qty) else (pt.list_price* sol.product_uom_qty) end) as ly_mnth_retail_amount
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty) else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end) as ly_mnth_invoice_amount 
                ,sum(case when pp.std_price= 0.0 then 0  else (pp.std_price * sol.product_uom_qty) end) as cost_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty)  else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_mnth_gross_amount
                ,0.0 as yr_retail_amount
                 ,0.0 as yr_invoice_amount
                 ,0.0 as yr_gross_amount
                 ,0.0 as ly_yr_retail_amount
                 ,0.0 as ly_yr_invoice_amount
                 ,0.0 as ly_yr_gross_amount 
            from sale_order_line sol
                inner join res_partner rp on (rp.id = sol.order_partner_id)
                inner join sale_order so on (so.id = sol.order_id)
                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                inner join account_move ai on (ai.id = ail.move_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where ai.state in ('open','paid') and 
                so.date_order >= '%s' 
                and so.date_order <= '%s' 
                and sol.order_partner_id in %s 
                and pt.exclude_from_report !=True
            UNION ALL
            select 
                sum(sol.product_uom_qty)
                ,0.0 as sale_price
                ,0.0 as invoice_price
                ,0.0 as gross_margin
                ,0.0 as ly_mnth_retail_amount
                 ,0.0 as ly_mnth_invoice_amount
                 ,0.0 as ly_mnth_gross_amount
                ,sum(case when pt.list_price = 0.0 then (sol.price_unit*sol.product_uom_qty) else (pt.list_price* sol.product_uom_qty) end) as yr_retail_amount
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty) else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end) as yr_invoice_amount 
                ,sum(case when pp.std_price= 0.0 then 0  else (pp.std_price * sol.product_uom_qty) end) as cost_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty)  else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as yr_gross_amount
                ,0.0 as ly_yr_retail_amount
                ,0.0 as ly_yr_invoice_amount
                ,0.0 as ly_yr_gross_amount 
            from sale_order_line sol
                inner join res_partner rp on (rp.id = sol.order_partner_id)
                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                inner join sale_order so on (so.id = sol.order_id)
                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                inner join account_move ai on (ai.id = ail.move_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where ai.state in ('open','paid') and 
                so.date_order >= '%s' 
                and so.date_order <= '%s' 
                and sol.order_partner_id in %s 
                and pt.exclude_from_report !=True

            UNION ALL
            select 
                 sum(sol.product_uom_qty)
                ,0.0 as sale_price
                ,0.0 as invoice_price
                ,0.0 as gross_margin
                ,0.0 as ly_mnth_retail_amount
                ,0.0 as ly_mnth_invoice_amount
                ,0.0 as ly_mnth_gross_amount
                ,0.0 as yr_retail_amount
                ,0.0 as yr_invoice_amount
                ,0.0 as yr_gross_amount
                ,sum(case when pt.list_price = 0.0 then (sol.price_unit*sol.product_uom_qty) else (pt.list_price* sol.product_uom_qty) end) as ly_yr_retail_amount
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty) else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end) as ly_yr_invoice_amount 
                ,sum(case when pp.std_price= 0.0 then 0  else (pp.std_price * sol.product_uom_qty) end) as cost_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sol.product_uom_qty)  else ((sol.price_unit*sol.product_uom_qty)* (sol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sol.product_uom_qty) end) as ly_yr_gross_amount
            from sale_order_line sol
                inner join res_partner rp on (rp.id = sol.order_partner_id)
                inner join sale_order_line_invoice_rel solir on (solir.order_line_id = sol.id)
                inner join sale_order so on (so.id = sol.order_id)
                inner join account_move_line ail on (ail.id = solir.invoice_line_id)
                inner join account_move ai on (ai.id = ail.move_id)
                inner join product_product pp on (sol.product_id = pp.id)
                inner join product_template pt on (pp.product_tmpl_id = pt.id)
                inner join product_category pc on (pc.id = pt.categ_id) 
            where ai.state in ('open','paid') and 
                so.date_order >= '%s' 
                and so.date_order <= '%s' 
                and sol.order_partner_id in %s 
                and pt.exclude_from_report !=True
            """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)
        print("sqllllllllll",sql)
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        retail_sale = 0
        invoice_sale = 0
        gross_margin = 0
        ly_mnth_retail_amount = 0
        ly_mnth_invoice_amount =  0
        ly_mnth_gross_amount = 0
        yr_retail_amount = 0
        yr_invoice_amount = 0
        yr_gross_amount = 0
        ly_yr_retail_amount =0
        ly_yr_invoice_amount = 0
        ly_yr_gross_amount = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            gross_margin += value.get('gross_margin', 0) or 0
            ly_mnth_retail_amount+= value.get('ly_mnth_retail_amount',0) or 0
            ly_mnth_invoice_amount+= value.get('ly_mnth_invoice_amount', 0) or 0
            ly_mnth_gross_amount += value.get('ly_mnth_gross_amount', 0) or 0
            yr_retail_amount+= value.get('yr_retail_amount',0) or 0
            yr_invoice_amount+= value.get('yr_invoice_amount', 0) or 0
            yr_gross_amount += value.get('yr_gross_amount', 0) or 0
            ly_yr_retail_amount+= value.get('ly_yr_retail_amount',0) or 0
            ly_yr_invoice_amount+= value.get('ly_yr_invoice_amount', 0) or 0
            ly_yr_gross_amount += value.get('ly_yr_gross_amount', 0) or 0

        return retail_sale, invoice_sale, gross_margin, ly_mnth_retail_amount, ly_mnth_invoice_amount, ly_mnth_gross_amount, yr_retail_amount, yr_invoice_amount,yr_gross_amount,ly_yr_retail_amount,ly_yr_invoice_amount,ly_yr_gross_amount

    def get_sale_amount_of_pos(self, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date, customer_ids, sale_type='sale', check_delivery=None):
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
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)

        sql = ("""
        select 
            sum(sm.product_uom_qty)
            ,sum(case when pt.list_price = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else (pt.list_price* sm.product_uom_qty) end) as sale_price_1
            ,sum(pol.price_subtotal) as sale_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as invoice_price_1
            ,sum(pol.price_subtotal) as invoice_price
            ,sum(case when pp.std_price= 0.0 then 0 
            else (pp.std_price * sm.product_uom_qty) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case 
            when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as gross_margin
            ,0.0 as ly_mnth_retail_amount_pos
            ,0.0 as ly_mnth_invoice_amount_pos
            ,0.0 as ly_mnth_gross_amount_pos
            ,0.0 as yr_retail_amount_pos
            ,0.0 as yr_invoice_amount_pos
            ,0.0 as yr_gross_amount_pos
            ,0.0 as ly_yr_retail_amount_pos
            ,0.0 as ly_yr_invoice_amount_pos
            ,0.0 as ly_yr_gross_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)          
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing') 
            and sm.product_id = pol.product_id
            and sm.state ='done'
            and po.partner_id in %s 
            and pt.exclude_from_report !=True 
        UNION ALL
        select 
            sum(sm.product_uom_qty)
            ,0.0 as sale_price
            ,0.0 as invoice_price
            ,0.0 as gross_margin
            ,sum(case when pt.list_price = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else (pt.list_price* sm.product_uom_qty) end) as sale_price_1
            ,sum(pol.price_subtotal) as ly_mnth_retail_amount_pos
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as invoice_price_1
            ,sum(pol.price_subtotal) as ly_mnth_invoice_amount_pos
            ,sum(case when pp.std_price= 0.0 then 0 
            else (pp.std_price * sm.product_uom_qty) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case 
            when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_mnth_gross_amount_pos
            ,0.0 as yr_retail_amount_pos
            ,0.0 as yr_invoice_amount_pos
            ,0.0 as yr_gross_amount_pos
            ,0.0 as ly_yr_retail_amount_pos
            ,0.0 as ly_yr_invoice_amount_pos
            ,0.0 as ly_yr_gross_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)          
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing') 
            and sm.product_id = pol.product_id
            and sm.state ='done'
            and po.partner_id in %s 
            and pt.exclude_from_report !=True
        UNION ALL
        select 
            sum(sm.product_uom_qty)
            ,0.0 as sale_price
            ,0.0 as invoice_price
            ,0.0 as gross_margin
            ,0.0 as ly_mnth_retail_amount_pos
            ,0.0 as ly_mnth_invoice_amount_pos
            ,0.0 as ly_mnth_gross_amount_pos
            ,sum(case when pt.list_price = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else (pt.list_price* sm.product_uom_qty) end) as sale_price_1
            ,sum(pol.price_subtotal) as yr_retail_amount_pos
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as invoice_price_1
            ,sum(pol.price_subtotal) as yr_invoice_amount_pos
            ,sum(case when pp.std_price= 0.0 then 0 
            else (pp.std_price * sm.product_uom_qty) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case 
            when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as yr_gross_amount_pos
            ,0.0 as ly_yr_retail_amount_pos
            ,0.0 as ly_yr_invoice_amount_pos
            ,0.0 as ly_yr_gross_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)          
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing') 
            and sm.product_id = pol.product_id
            and sm.state ='done'
            and po.partner_id in %s 
            and pt.exclude_from_report !=True
        UNION ALL
        select 
            sum(sm.product_uom_qty)
            ,0.0 as sale_price
            ,0.0 as invoice_price
            ,0.0 as gross_margin
            ,0.0 as ly_mnth_retail_amount_pos
            ,0.0 as ly_mnth_invoice_amount_pos
            ,0.0 as ly_mnth_gross_amount_pos
            ,0.0 as yr_retail_amount_pos
            ,0.0 as yr_invoice_amount_pos
            ,0.0 as yr_gross_amount_pos
            ,sum(case when pt.list_price = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else (pt.list_price* sm.product_uom_qty) end) as sale_price_1
            ,sum(pol.price_subtotal) as ly_yr_retail_amount_pos
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as invoice_price_1
            ,sum(pol.price_subtotal) as ly_yr_invoice_amount_pos
            ,sum(case when pp.std_price= 0.0 then 0 
            else (pp.std_price * sm.product_uom_qty) end) as cost_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case 
            when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end) as ly_yr_gross_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)          
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing') 
            and sm.product_id = pol.product_id
            and sm.state ='done'
            and po.partner_id in %s 
            and pt.exclude_from_report !=True


        """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        retail_sale = 0
        invoice_sale = 0
        gross_margin = 0
        ly_mnth_retail_amount_pos = 0
        ly_mnth_invoice_amount_pos = 0 
        ly_mnth_gross_amount_pos = 0
        yr_retail_amount_pos = 0
        yr_invoice_amount_pos = 0
        yr_gross_amount_pos = 0
        ly_yr_retail_amount_pos = 0
        ly_yr_invoice_amount_pos = 0
        ly_yr_gross_amount_pos = 0
        for value in result:
            retail_sale += value.get('sale_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            gross_margin += value.get('gross_margin', 0) or 0
            ly_mnth_retail_amount_pos+= value.get('ly_mnth_retail_amount_pos',0) or 0
            ly_mnth_invoice_amount_pos += value.get('ly_mnth_invoice_amount_pos', 0) or 0
            ly_mnth_gross_amount_pos += value.get('ly_mnth_gross_amount_pos', 0) or 0
            yr_retail_amount_pos += value.get('yr_retail_amount_pos', 0) or 0
            yr_invoice_amount_pos += value.get('yr_invoice_amount_pos', 0) or 0
            yr_gross_amount_pos += value.get('yr_gross_amount_pos', 0) or 0
            ly_yr_retail_amount_pos += value.get('ly_yr_retail_amount_pos', 0) or 0
            ly_yr_invoice_amount_pos += value.get('ly_yr_invoice_amount_pos', 0) or 0
            ly_yr_gross_amount_pos += value.get('ly_yr_gross_amount_pos', 0) or 0
        return retail_sale, invoice_sale, gross_margin,ly_mnth_retail_amount_pos,ly_mnth_invoice_amount_pos,ly_mnth_gross_amount_pos,yr_retail_amount_pos,yr_invoice_amount_pos,yr_gross_amount_pos,ly_yr_retail_amount_pos,ly_yr_invoice_amount_pos,ly_yr_gross_amount_pos
    
    def get_so_return_amount_of_pos(self, customer_ids, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date):
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
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)
        sale_type = 'sale'

        sql = ("""
        select 
            sum(sm.product_uom_qty)
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as invoice_price
        ,0.0 as ly_mnth_so_return_amount_pos
        ,0.0 as yr_so_return_amount_pos
        ,0.0 as ly_yr_so_return_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('incoming') 
            and sm.state='done'
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True 
        UNION ALL
        select 
            sum(sm.product_uom_qty)
            ,0.0 as invoice_price
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as ly_mnth_so_return_amount_pos 
            ,0.0 as yr_so_return_amount_pos
            ,0.0 as ly_yr_so_return_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('incoming') 
            and sm.state='done'
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True 
        UNION ALL
        select 
            sum(sm.product_uom_qty)
            ,0.0 as invoice_price
            ,0.0 as ly_mnth_so_return_amount_pos
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as yr_so_return_amount_pos
            ,0.0 as ly_yr_so_return_amount_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('incoming')
            and sm.state='done' 
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True 
        UNION ALL
        select 
            sum(sm.product_uom_qty)
            ,0.0 as invoice_price
            ,0.0 as ly_mnth_so_return_amount_pos
            ,0.0 as yr_so_return_amount_pos
            ,sum(case when pol.discount = 0.0 then (pol.price_unit*sm.product_uom_qty) 
            else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end) as ly_yr_so_return_amount_pos 
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id) or (sp.pos_session_id = po.session_id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('incoming')
            and sm.state='done'
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True 

        """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)

        self._cr.execute(sql)
        res = self._cr.dictfetchall()

        mnth_so_return_amount = 0
        ly_mnth_so_return_amount_pos = 0
        yr_so_return_amount_pos =0
        ly_yr_so_return_amount_pos = 0
        for value in res:
            mnth_so_return_amount += value.get('invoice_price', 0) or 0
            ly_mnth_so_return_amount_pos += value.get('ly_mnth_so_return_amount_pos', 0) or 0
            yr_so_return_amount_pos += value.get('yr_so_return_amount_pos', 0) or 0
            ly_yr_so_return_amount_pos += value.get('ly_yr_so_return_amount_pos', 0) or 0
        return -abs(mnth_so_return_amount),abs(ly_mnth_so_return_amount_pos), abs(yr_so_return_amount_pos), abs(ly_yr_so_return_amount_pos)

    def get_so_return_amount(self, customer_ids, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date):
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
        if date_to:
            date_to += ' 23:59:59'

        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)
        sale_type = 'sale'

        sql = ("""
            select 
                sum(sm.product_uom_qty)
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty) 
                else ((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0 end) as invoice_price 
                ,0.0 as ly_mnth_so_return_amount
                ,0.0 as yr_so_return_amount
                ,0.0 as ly_yr_so_return_amount
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
                and spt.code='incoming'
                and sm.state ='done' 
                and sm.product_id = sol.product_id 
                and so.partner_id in %s
               and pt.exclude_from_report !=True 
            UNION ALL
            select 
                sum(sm.product_uom_qty)
                ,0.0 as invoice_price
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty) 
                else ((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0 end) as ly_mnth_so_return_amount
                ,0.0 as yr_so_return_amount
                ,0.0 as ly_yr_so_return_amount 
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
                and spt.code='incoming' 
                and sm.state ='done' 
                and sm.product_id = sol.product_id 
                and so.partner_id in %s
               and pt.exclude_from_report !=True 
            UNION ALL
            select 
                sum(sm.product_uom_qty)
                ,0.0 as invoice_price
                ,0.0 as ly_mnth_so_return_amount
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty) 
                else ((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0 end) as yr_so_return_amount
                ,0.0 as ly_yr_so_return_amount   
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
                and spt.code='incoming'
                and sm.state ='done' 
                and sm.product_id = sol.product_id 
                and so.partner_id in %s
               and pt.exclude_from_report !=True 
            UNION ALL
            select 
                sum(sm.product_uom_qty)
                ,0.0 as invoice_price
                ,0.0 as ly_mnth_so_return_amount
                ,0.0 as yr_so_return_amount
                ,sum(case when sol.discount = 0.0 then (sol.price_unit*sm.product_uom_qty) 
                else ((sol.price_unit*sm.product_uom_qty)* (sol.discount))/100.0 end) as ly_yr_so_return_amount  
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
                and spt.code='incoming'
                and sm.state ='done'  
                and sm.product_id = sol.product_id 
                and so.partner_id in %s
               and pt.exclude_from_report !=True 

            """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)

        self._cr.execute(sql)
        res = self._cr.dictfetchall()

        mnth_so_return_amount = 0
        ly_mnth_so_return_amount = 0
        yr_so_return_amount = 0
        ly_yr_so_return_amount = 0


        for value in res:
            mnth_so_return_amount += value.get('invoice_price', 0) or 0
            ly_mnth_so_return_amount += value.get('ly_mnth_so_return_amount', 0) or 0
            yr_so_return_amount += value.get('yr_so_return_amount', 0) or 0
            ly_yr_so_return_amount += value.get('ly_yr_so_return_amount', 0) or 0
        return -abs(mnth_so_return_amount),abs(ly_mnth_so_return_amount), abs(yr_so_return_amount), abs(ly_yr_so_return_amount)

    def get_net_sales(self, total_sale, sales_return):
        ns_mtd = total_sale[2] + sales_return[2]
        ns_lymtd = total_sale[3] + sales_return[3]
        ns_minc_dec = ns_lymtd and (ns_mtd - ns_lymtd) / ns_lymtd or 0
        ns_ytd = total_sale[5] + sales_return[5]
        ns_lytd = total_sale[6] + sales_return[6]
        ns_yinc_dec = ns_lytd and (float(ns_ytd) - float(ns_lytd)) / float(ns_lytd) or 0
        net_sales = ['Net Sale', 'amount']
        net_sales.append(ns_mtd)
        net_sales.append(ns_lymtd)
        net_sales.append(str(round(ns_minc_dec * 100, 2)) + '%')
        net_sales.append(ns_ytd)
        net_sales.append(ns_lytd)
        net_sales.append(str(round(ns_yinc_dec * 100, 2)) + '%')
        return net_sales

    def get_gross_percentage(self, gross_amount, net_invoice):
        gp_mtd = net_invoice[2] and gross_amount[2] / net_invoice[2] or 0
        gp_lymtd = net_invoice[3] and gross_amount[3] / net_invoice[3] or 0
        gp_minc_dec = gp_lymtd and (gp_mtd - gp_lymtd) or 0
        gp_ytd = net_invoice[5] and gross_amount[5] / net_invoice[5] or 0
        gp_lytd = net_invoice[6] and gross_amount[6] / net_invoice[6] or 0
        gp_yinc_dec = gp_lytd and (float(gp_ytd) - float(gp_lytd)) or 0
        gross_percentage = ['Gross Margin %', 'perc']
        gross_percentage.append(str(round(gp_mtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_lymtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_minc_dec * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_ytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_lytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_yinc_dec * 100, 2)) + '%')
        return gross_percentage

    def get_sale_count(self, date_from, date_to,last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date, customer_ids, sale_type='sale'):
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
        if date_to:
            date_to += ' 23:59:59'
        date_from = self.get_date_with_tz(date_from)
        date_to = self.get_date_with_tz(date_to)
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)
        last_yr_date_to = self.get_date_with_tz(last_yr_date_to)
        fiscalyear_start_date = self.get_date_with_tz(fiscalyear_start_date)
        last_yr_fiscalyear_start_date = self.get_date_with_tz(last_yr_fiscalyear_start_date)
        sql = ("""
        select 
            SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
            when pt.type = 'service' then sol.qty_delivered ELSE 0 END) as net_qty_1,
            sum(sol.qty_delivered) as net_qty,
            count(distinct so.id) as sale_count
            ,0.0 as ly_m_item_count
            ,0.0 as ly_m_sale_count
            ,0.0 as y_item_count
            ,0.0 as y_sale_count
            ,0.0 as ly_y_item_count
            ,0.0 as ly_y_sale_count
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
            and so.partner_id in %s
            and pt.exclude_from_report !=True
        UNION ALL
        select 
            0.0 as net_qty
            ,0.0 as sale_count
            ,SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
            when pt.type = 'service' then sol.qty_delivered ELSE 0 END) as net_qty_1,
            sum(sol.qty_delivered) as ly_m_item_count,
            count(distinct so.id) as ly_m_sale_count
            ,0.0 as y_item_count
            ,0.0 as y_sale_count
            ,0.0 as ly_y_item_count
            ,0.0 as ly_y_sale_count
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
            and so.partner_id in %s
            and pt.exclude_from_report !=True
        UNION ALL
        select
             0.0 as net_qty
            ,0.0 as sale_count
            ,0.0 as ly_m_item_count
            ,0.0 as ly_m_sale_count
            ,SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
            when pt.type = 'service' then sol.qty_delivered ELSE 0 END) as net_qty_1,
            sum(sol.qty_delivered) as y_item_count,
            count(distinct so.id) as y_sale_count
            ,0.0 as ly_y_item_count
            ,0.0 as ly_y_sale_count
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
            and so.partner_id in %s
            and pt.exclude_from_report !=True
        UNION ALL
        select
         0.0 as net_qty
        ,0.0 as sale_count
        ,0.0 as ly_m_item_count
        ,0.0 as ly_m_sale_count
        ,0.0 as y_item_count
        ,0.0 as y_sale_count
        ,SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
            when pt.type = 'service' then sol.qty_delivered ELSE 0 END) as net_qty_1,
            sum(sol.qty_delivered) as ly_y_item_count,
            count(distinct so.id) as ly_y_sale_count
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
            and so.partner_id in %s
            and pt.exclude_from_report !=True

        """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)
        print("sql:::",sql)
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        sale_count = 0
        product_count = 0
        ly_m_sale_count = 0
        ly_m_item_count = 0
        y_sale_count =0
        y_item_count =0
        ly_y_sale_count = 0
        ly_y_item_count =0



        for value in res:
            product_count += value.get('net_qty', 0) or 0
            sale_count += value.get('sale_count', 0) or 0
            ly_m_item_count += value.get('ly_m_item_count', 0) or 0
            ly_m_sale_count += value.get('ly_m_sale_count', 0) or 0
            y_item_count += value.get('y_item_count', 0) or 0
            y_sale_count += value.get('y_sale_count', 0) or 0
            ly_y_item_count += value.get('ly_y_item_count', 0) or 0
            ly_y_sale_count += value.get('ly_y_sale_count', 0) or 0
        return sale_count, product_count,ly_m_sale_count,ly_m_item_count,y_sale_count,y_item_count,ly_y_sale_count,ly_y_item_count

    def get_sale_count_of_pos(self, date_from, date_to, last_yr_month_start_date,last_yr_date_to,fiscalyear_start_date,last_yr_fiscalyear_start_date,customer_ids, sale_type='sale'):
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
        if date_to:
            date_to += ' 23:59:59'
        last_yr_month_start_date = self.get_date_with_tz(last_yr_month_start_date)

        sql = ("""
        select 
            SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) as net_qty,
            count(distinct po.id) as sale_count
            ,0.0 as ly_m_item_count_pos
            ,0.0 as ly_m_sale_count_pos
            ,0.0 as y_item_count_pos
            ,0.0 as y_sale_count_pos
            ,0.0 as ly_y_item_count_pos
            ,0.0 as ly_y_sale_count_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing', 'incoming')
            and sm.state='done' 
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True
        UNION ALL
        select
            0.0 as net_qty
            ,0.0 as sale_count
            ,SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) as ly_m_item_count_pos,
            count(distinct po.id) as ly_m_sale_count_pos
            ,0.0 as y_item_count_pos
            ,0.0 as y_sale_count_pos
            ,0.0 as ly_y_item_count_pos
            ,0.0 as ly_y_sale_count_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing', 'incoming')
            and sm.state='done' 
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True
        UNION ALL
        select
            0.0 as net_qty
            ,0.0 as sale_count
            ,0.0 as ly_m_item_count_pos
            ,0.0 as ly_m_sale_count_pos
            ,SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) as y_item_count_pos,
            count(distinct po.id) as y_sale_count_pos
            ,0.0 as ly_y_item_count_pos
            ,0.0 as ly_y_sale_count_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing', 'incoming')
            and sm.state='done' 
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True
        UNION ALL
        select
             0.0 as net_qty
            ,0.0 as sale_count
            ,0.0 as ly_m_item_count_pos
            ,0.0 as ly_m_sale_count_pos
            ,0.0 as y_item_count_pos
            ,0.0 as y_sale_count_pos
            ,SUM(CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
            WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty) ELSE 0 END) as ly_y_item_count_pos,
            count(distinct po.id) as ly_y_sale_count_pos
        from pos_order_line pol
            inner join pos_order po on (po.id = pol.order_id)
            inner join stock_picking sp on (sp.pos_order_id = po.id)
            inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            inner join stock_move sm on (sp.id = sm.picking_id)
            inner join res_partner rp on (rp.id = po.partner_id)
            inner join product_product pp on (sm.product_id = pp.id)
            inner join product_template pt on (pp.product_tmpl_id = pt.id)
            inner join product_category pc on (pc.id = pt.categ_id) 
        where sp.date_done >= '%s' 
            and sp.date_done <= '%s'
            and sp.state = 'done' 
            and spt.code in ('outgoing', 'incoming')
            and sm.state='done' 
            and sm.product_id = pol.product_id
            and po.partner_id in %s 
            and pt.exclude_from_report !=True

        """) % (date_from, date_to, customer_ids,last_yr_month_start_date,last_yr_date_to,customer_ids,fiscalyear_start_date,date_to,customer_ids,last_yr_fiscalyear_start_date,last_yr_date_to,customer_ids)

        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        sale_count = 0
        product_count = 0
        ly_m_sale_count_pos = 0
        ly_m_item_count_pos =0
        y_item_count_pos= 0
        y_sale_count_pos = 0
        ly_y_sale_count_pos = 0
        ly_y_item_count_pos = 0
        for value in res:
            product_count += value.get('net_qty', 0) or 0
            sale_count += value.get('sale_count', 0) or 0
            product_count += value.get('ly_m_item_count_pos', 0) or 0
            sale_count += value.get('ly_m_sale_count_pos', 0) or 0
            product_count += value.get('y_item_count_pos', 0) or 0
            sale_count += value.get('y_sale_count_pos', 0) or 0
            product_count += value.get('ly_y_item_count_pos', 0) or 0
            sale_count += value.get('ly_y_item_count_pos', 0) or 0
 
        return sale_count, product_count,ly_m_sale_count_pos,ly_m_item_count_pos,y_sale_count_pos,y_item_count_pos,ly_y_sale_count_pos,ly_y_item_count_pos

    def get_transaction_lines(self, net_sale_list, month_start_date, date_to,
                              last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                              last_yr_fiscalyear_start_date):
        context = self.env.context
        if 'options' in context:
            customer_ids = self.env['res.partner'].browse(context['options']['partner_ids'])
        else:
            customer_ids = context.get('partner_ids', [])
        if not customer_ids:
            customer_ids = self.env['res.partner'].search([('customer_rank', '>', 0)])
        transaction_list = []
        if customer_ids:
            customer_ids = customer_ids.ids
            customer_ids_str = ','.join(str(x) for x in customer_ids)
            customer_ids = '(' + customer_ids_str + ')'

            sale_count = ['# Sales', 'count']
            item_count = ['# Items Sold', 'count']
            avg_sale = ['Average Dollars Sale', 'amount']
            aunitsale = ['Average Units per Sale', 'number']

            m_sale_count, m_item_count,ly_m_sale_count,ly_m_item_count,y_sale_count,y_item_count,ly_y_sale_count,ly_y_item_count = self.get_sale_count(str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date), customer_ids)
            m_sale_count_pos, m_item_count_pos, ly_m_sale_count_pos, ly_m_item_count_pos,y_sale_count_pos, y_item_count_pos,ly_y_sale_count_pos, ly_y_item_count_pos = self.get_sale_count_of_pos(str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),customer_ids)
           
            print(" m_sale_count, m_item_count,ly_m_sale_count,ly_m_item_count,y_sale_count,y_item_count,ly_y_sale_count,ly_y_item_count", m_sale_count, m_item_count,ly_m_sale_count,ly_m_item_count,y_sale_count,y_item_count,ly_y_sale_count,ly_y_item_count)
            print(" m_sale_count_pos, m_item_count_pos, ly_m_sale_count_pos, ly_m_item_count_pos,y_sale_count_pos, y_item_count_pos,ly_y_sale_count_pos, ly_y_item_count_pos", m_sale_count_pos, m_item_count_pos, ly_m_sale_count_pos, ly_m_item_count_pos,y_sale_count_pos, y_item_count_pos,ly_y_sale_count_pos, ly_y_item_count_pos)
            m_sale_count = m_sale_count + m_sale_count_pos
            m_item_count = m_item_count + m_item_count_pos
            m_avg_unit = m_sale_count and round(m_item_count / m_sale_count, 2) or 0
            m_avg_sale = m_sale_count and round(net_sale_list[2] / m_sale_count, 2) or 0

            ly_m_sale_count = ly_m_sale_count + ly_m_sale_count_pos
            ly_m_item_count = ly_m_item_count + ly_m_item_count_pos

            ly_m_avg_unit = ly_m_sale_count and round(ly_m_item_count / ly_m_sale_count, 2) or 0
            ly_m_avg_sale = ly_m_sale_count and round(net_sale_list[3] / ly_m_sale_count, 2) or 0

            m_sale_inc_dec = ly_m_sale_count and (float(m_sale_count) - float(ly_m_sale_count)) / float(
                ly_m_sale_count) or 0
            m_item_inc_dec = ly_m_item_count and (float(m_item_count) - float(ly_m_item_count)) / float(
                ly_m_item_count) or 0
            m_avg_unit_inc_dec = ly_m_avg_unit and (m_avg_unit - ly_m_avg_unit) / ly_m_avg_unit or 0
            m_avg_sale_inc_dec = ly_m_avg_sale and (m_avg_sale - ly_m_avg_sale) / ly_m_avg_sale or 0

            y_sale_count = y_sale_count + y_sale_count_pos
            y_item_count = y_item_count + y_item_count_pos

            y_avg_unit = y_sale_count and round(y_item_count / y_sale_count, 2) or 0
            y_avg_sale = y_sale_count and round(net_sale_list[5] / y_sale_count, 2) or 0

            ly_y_sale_count = ly_y_sale_count + ly_y_sale_count_pos
            ly_y_item_count = ly_y_item_count + ly_y_item_count_pos

            ly_y_avg_unit = ly_y_sale_count and round(ly_y_item_count / ly_y_sale_count, 2) or 0
            ly_y_avg_sale = ly_y_sale_count and round(net_sale_list[6] / ly_y_sale_count, 2) or 0

            y_sale_inc_dec = ly_y_sale_count and (float(y_sale_count) - float(ly_y_sale_count)) / float(
                ly_y_sale_count) or 0
            y_item_inc_dec = ly_y_item_count and (float(y_item_count) - float(ly_y_item_count)) / float(
                ly_y_item_count) or 0
            y_avg_unit_inc_dec = ly_y_avg_unit and (y_avg_unit - ly_y_avg_unit) / ly_y_avg_unit or 0
            y_avg_sale_inc_dec = ly_y_avg_sale and (y_avg_sale - ly_y_avg_sale) / ly_y_avg_sale or 0

            sale_count.append(m_sale_count)
            sale_count.append(ly_m_sale_count)
            sale_count.append(str(round(m_sale_inc_dec * 100, 2)) + '%')
            sale_count.append(y_sale_count)
            sale_count.append(ly_y_sale_count)
            sale_count.append(str(round(y_sale_inc_dec * 100, 2)) + '%')

            item_count.append(m_item_count)
            item_count.append(ly_m_item_count)
            item_count.append(str(round(m_item_inc_dec * 100, 2)) + '%')
            item_count.append(y_item_count)
            item_count.append(ly_y_item_count)
            item_count.append(str(round(y_item_inc_dec * 100, 2)) + '%')

            avg_sale.append(m_avg_sale)
            avg_sale.append(ly_m_avg_sale)
            avg_sale.append(str(round(m_avg_sale_inc_dec * 100, 2)) + '%')
            avg_sale.append(y_avg_sale)
            avg_sale.append(ly_y_avg_sale)
            avg_sale.append(str(round(y_avg_sale_inc_dec * 100, 2)) + '%')

            aunitsale.append(m_avg_unit)
            aunitsale.append(ly_m_avg_unit)
            aunitsale.append(str(round(m_avg_unit_inc_dec * 100, 2)) + '%')
            aunitsale.append(y_avg_unit)
            aunitsale.append(ly_y_avg_unit)
            aunitsale.append(str(round(y_avg_unit_inc_dec * 100, 2)) + '%')

            transaction_list.append(sale_count)
            transaction_list.append(item_count)
            transaction_list.append(avg_sale)
            transaction_list.append(aunitsale)
        return transaction_list

    def get_gross_percentage_for_repair_service(self, gross_amount, net_invoice):
        gp_mtd = net_invoice[2] and gross_amount[2] / net_invoice[2] or 0
        gp_lymtd = net_invoice[3] and gross_amount[3] / net_invoice[3] or 0
        gp_minc_dec = gp_lymtd and (gp_mtd - gp_lymtd) or 0
        gp_ytd = net_invoice[5] and gross_amount[5] / net_invoice[5] or 0
        gp_lytd = net_invoice[6] and gross_amount[6] / net_invoice[6] or 0
        gp_yinc_dec = gp_lytd and (gp_ytd - gp_lytd) or 0
        gross_percentage = ['Gross Margin %', 'perc']
        gross_percentage.append(str(round(gp_mtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_lymtd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_minc_dec * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_ytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_lytd * 100, 2)) + '%')
        gross_percentage.append(str(round(gp_yinc_dec * 100, 2)) + '%')
        return gross_percentage

    def get_repair_service_lines(self, row_name, sale_type, month_start_date, date_to,
                                 last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                 last_yr_fiscalyear_start_date):
        context = self.env.context
        if 'options' in context:
            customer_ids = self.env['res.partner'].browse(context['options']['partner_ids'])
        else:
            customer_ids = context.get('partner_ids', [])
        if not customer_ids:
            customer_ids = self.env['res.partner'].search([('customer_rank', '>', 0)])
        line_list = []
        if customer_ids:
            customer_ids = customer_ids.ids
            customer_ids_str = ','.join(str(x) for x in customer_ids)
            customer_ids = '(' + customer_ids_str + ')'

            (mnth_retail_amount, mnth_invoice_amount,
             mnth_gross_amount,ly_mnth_retail_amount, ly_mnth_invoice_amount, ly_mnth_gross_amount,
             yr_retail_amount, yr_invoice_amount,yr_gross_amount,
             ly_yr_retail_amount, ly_yr_invoice_amount, ly_yr_gross_amount) = self.get_sale_amount(str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date), customer_ids, sale_type)
            (mnth_retail_amount_pos, mnth_invoice_amount_pos,
             mnth_gross_amount_pos, ly_mnth_retail_amount_pos, ly_mnth_invoice_amount_pos, ly_mnth_gross_amount_pos,
             yr_retail_amount_pos, yr_invoice_amount_pos,yr_gross_amount_pos, ly_yr_retail_amount_pos, ly_yr_invoice_amount_pos, ly_yr_gross_amount_pos) = self.get_sale_amount_of_pos(str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),customer_ids, sale_type)
            mnth_retail_amount = mnth_retail_amount + mnth_retail_amount_pos
            mnth_invoice_amount = mnth_invoice_amount + mnth_invoice_amount_pos
            mnth_gross_amount = mnth_gross_amount + mnth_gross_amount_pos
            ly_mnth_retail_amount = ly_mnth_retail_amount + ly_mnth_retail_amount_pos
            ly_mnth_invoice_amount = ly_mnth_invoice_amount + ly_mnth_invoice_amount_pos
            ly_mnth_gross_amount = ly_mnth_gross_amount + ly_mnth_gross_amount_pos

            mnth_invoice_inc_dec = ly_mnth_invoice_amount and (
                    mnth_invoice_amount - ly_mnth_invoice_amount) / ly_mnth_invoice_amount or 0
            mnth_gross_inc_dec = ly_mnth_gross_amount and (
                    mnth_gross_amount - ly_mnth_gross_amount) / ly_mnth_gross_amount or 0

            yr_retail_amount = yr_retail_amount + yr_retail_amount_pos
            yr_invoice_amount = yr_invoice_amount + yr_invoice_amount_pos
            yr_gross_amount = yr_gross_amount + yr_gross_amount_pos

            ly_yr_retail_amount = ly_yr_retail_amount + ly_yr_retail_amount_pos
            ly_yr_invoice_amount = ly_yr_invoice_amount + ly_yr_invoice_amount_pos
            ly_yr_gross_amount = ly_yr_gross_amount + ly_yr_gross_amount_pos
            yr_invoice_inc_dec = ly_yr_invoice_amount and (
                    yr_invoice_amount - ly_yr_invoice_amount) / ly_yr_invoice_amount or 0
            yr_gross_inc_dec = ly_yr_gross_amount and (yr_gross_amount - ly_yr_gross_amount) / ly_yr_gross_amount or 0

            invoice_sale = [row_name + ' Sold', 'amount']
            invoice_sale.append(mnth_invoice_amount)
            invoice_sale.append(ly_mnth_invoice_amount)
            invoice_sale.append(str(round(mnth_invoice_inc_dec * 100, 2)) + '%')
            invoice_sale.append(yr_invoice_amount)
            invoice_sale.append(ly_yr_invoice_amount)
            invoice_sale.append(str(round(yr_invoice_inc_dec * 100, 2)) + '%')

            gross_margin = ['Gross Margin $', 'amount']
            gross_margin.append(round(mnth_gross_amount, 2))
            gross_margin.append(round(ly_mnth_gross_amount, 2))
            gross_margin.append(str(round(mnth_gross_inc_dec * 100, 2)) + '%')
            gross_margin.append(round(yr_gross_amount, 2))
            gross_margin.append(round(ly_yr_gross_amount, 2))
            gross_margin.append(str(round(yr_gross_inc_dec * 100, 2)) + '%')

            gross_percetage = self.get_gross_percentage_for_repair_service(gross_margin, invoice_sale)

            line_list.append(invoice_sale)
            line_list.append(gross_margin)
            line_list.append(gross_percetage)
        return line_list

    def get_sale_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                       fiscalyear_start_date, last_yr_fiscalyear_start_date):
        context = self.env.context
        if 'options' in context:
            customer_ids =self.env['res.partner'].browse(context['options']['partner_ids'])
        else:
            customer_ids = context.get('partner_ids', [])
        print("customer_ids",customer_ids)
        if not customer_ids:
            customer_ids = self.env['res.partner'].search([('customer_rank', '>', 0)])
        sales_list = []
        if customer_ids:
            customer_ids = customer_ids.ids
            customer_ids_str = ','.join(str(x) for x in customer_ids)
            customer_ids = '(' + customer_ids_str + ')'

            retail_sale = ['Retail', 'amount']
            invoice_sale = ['Total Sold', 'amount']
            returned_sale = ['Returned', 'amount']
            gross_margin = ['Gross Margin $', 'amount']
            (mnth_retail_amount,mnth_invoice_amount,mnth_gross_amount,
             ly_mnth_retail_amount,ly_mnth_invoice_amount,ly_mnth_gross_amount,
             yr_retail_amount,yr_invoice_amount,yr_gross_amount,
             ly_yr_retail_amount,ly_yr_invoice_amount,ly_yr_gross_amount,) = self.get_sale_amount(str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),customer_ids,check_delivery=True)
        
            (mnth_retail_amount_pos, mnth_invoice_amount_pos,
             mnth_gross_amount_pos,ly_mnth_retail_amount_pos,ly_mnth_invoice_amount_pos,ly_mnth_gross_amount_pos,
             yr_retail_amount_pos,yr_invoice_amount_pos,yr_gross_amount_pos,
             ly_yr_retail_amount_pos,ly_yr_invoice_amount_pos,ly_yr_gross_amount_pos) = self.get_sale_amount_of_pos(str(month_start_date), date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date),
                                                                  customer_ids, check_delivery=True)
            mnth_retail_amount = mnth_retail_amount + mnth_retail_amount_pos
            mnth_invoice_amount = mnth_invoice_amount + mnth_invoice_amount_pos
            mnth_gross_amount = mnth_gross_amount + mnth_gross_amount_pos
            mnth_so_return_amount,ly_mnth_so_return_amount,yr_so_return_amount,ly_yr_so_return_amount= self.get_so_return_amount(customer_ids,str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date))
            # mnth_so_return_amount = self.get_so_return_amount(customer_ids, str(month_start_date), date_to)
            mnth_so_return_amount_pos, ly_mnth_so_return_amount_pos,yr_so_return_amount_pos,ly_yr_so_return_amount_pos= self.get_so_return_amount_of_pos(customer_ids, str(month_start_date),date_to,str(last_yr_month_start_date),str(last_yr_date_to),str(fiscalyear_start_date),str(last_yr_fiscalyear_start_date))
            mnth_so_return_amount = mnth_so_return_amount + mnth_so_return_amount_pos

            ly_mnth_retail_amount = ly_mnth_retail_amount + ly_mnth_retail_amount_pos
            ly_mnth_invoice_amount = ly_mnth_invoice_amount + ly_mnth_invoice_amount_pos
            ly_mnth_gross_amount = ly_mnth_gross_amount + ly_mnth_gross_amount_pos
            ly_mnth_so_return_amount = ly_mnth_so_return_amount + ly_mnth_so_return_amount_pos

            mnth_retail_inc_dec = ly_mnth_retail_amount and (
                    mnth_retail_amount - ly_mnth_retail_amount) / ly_mnth_retail_amount or 0
            mnth_invoice_inc_dec = ly_mnth_invoice_amount and (
                    mnth_invoice_amount - ly_mnth_invoice_amount) / ly_mnth_invoice_amount or 0
            mnth_gross_inc_dec = ly_mnth_gross_amount and (
                    mnth_gross_amount - ly_mnth_gross_amount) / ly_mnth_gross_amount or 0
            mnth_so_return_inc_dec = ly_mnth_so_return_amount and (
                    mnth_so_return_amount - ly_mnth_so_return_amount) / ly_mnth_so_return_amount or 0

            yr_retail_amount = yr_retail_amount + yr_retail_amount_pos
            yr_invoice_amount = yr_invoice_amount + yr_invoice_amount_pos
            yr_gross_amount = yr_gross_amount + yr_gross_amount_pos

            yr_so_return_amount = yr_so_return_amount + yr_so_return_amount_pos
    
            ly_yr_retail_amount = ly_yr_retail_amount + ly_yr_retail_amount_pos
            ly_yr_invoice_amount = ly_yr_invoice_amount + ly_yr_invoice_amount_pos
            ly_yr_gross_amount = ly_yr_gross_amount + ly_yr_gross_amount_pos
            ly_yr_so_return_amount = ly_yr_so_return_amount + ly_yr_so_return_amount_pos
            yr_retail_inc_dec = ly_yr_retail_amount and (
                    yr_retail_amount - ly_yr_retail_amount) / ly_yr_retail_amount or 0
            yr_invoice_inc_dec = ly_yr_invoice_amount and (
                    yr_invoice_amount - ly_yr_invoice_amount) / ly_yr_invoice_amount or 0
            yr_gross_inc_dec = ly_yr_gross_amount and (yr_gross_amount - ly_yr_gross_amount) / ly_yr_gross_amount or 0
            yr_so_return_inc_dec = ly_yr_so_return_amount and (
                    yr_so_return_amount - ly_yr_so_return_amount) / ly_yr_so_return_amount or 0

            retail_sale.append(mnth_retail_amount)
            retail_sale.append(ly_mnth_retail_amount)
            retail_sale.append(str(round(mnth_retail_inc_dec * 100, 2)) + '%')
            retail_sale.append(yr_retail_amount)
            retail_sale.append(ly_yr_retail_amount)
            retail_sale.append(str(round(yr_retail_inc_dec * 100, 2)) + '%')

            invoice_sale.append(mnth_invoice_amount)
            invoice_sale.append(ly_mnth_invoice_amount)
            invoice_sale.append(str(round(mnth_invoice_inc_dec * 100, 2)) + '%')
            invoice_sale.append(yr_invoice_amount)
            invoice_sale.append(ly_yr_invoice_amount)
            invoice_sale.append(str(round(yr_invoice_inc_dec * 100, 2)) + '%')

            gross_margin.append(round(mnth_gross_amount, 2))
            gross_margin.append(round(ly_mnth_gross_amount, 2))
            gross_margin.append(str(round(mnth_gross_inc_dec * 100, 2)) + '%')
            gross_margin.append(round(yr_gross_amount, 2))
            gross_margin.append(round(ly_yr_gross_amount, 2))
            gross_margin.append(str(round(yr_gross_inc_dec * 100, 2)) + '%')

            returned_sale.append(mnth_so_return_amount)
            returned_sale.append(ly_mnth_so_return_amount)
            returned_sale.append(str(round(mnth_so_return_inc_dec * 100, 2)) + '%')
            returned_sale.append(yr_so_return_amount)
            returned_sale.append(ly_yr_so_return_amount)
            returned_sale.append(str(round(yr_so_return_inc_dec * 100, 2)) + '%')

            discount_amount = ['Discount $', 'amount']
            mnth_discount_amount = mnth_retail_amount - mnth_invoice_amount
            ly_mnth_discount_amount = ly_mnth_retail_amount - ly_mnth_invoice_amount
            mnth_discount_inc_dec = ly_mnth_discount_amount and (
                    mnth_discount_amount - ly_mnth_discount_amount) / ly_mnth_discount_amount or 0
            yr_discount_amount = yr_retail_amount - yr_invoice_amount
            ly_yr_discount_amount = ly_yr_retail_amount - ly_yr_invoice_amount
            yr_discount_inc_dec = ly_yr_discount_amount and (
                    yr_discount_amount - ly_yr_discount_amount) / ly_yr_discount_amount or 0

            discount_amount.append(mnth_discount_amount)
            discount_amount.append(ly_mnth_discount_amount)
            discount_amount.append(str(round(mnth_discount_inc_dec * 100, 2)) + '%')
            discount_amount.append(yr_discount_amount)
            discount_amount.append(ly_yr_discount_amount)
            discount_amount.append(str(round(yr_discount_inc_dec * 100, 2)) + '%')

            discount_percentage = ['Discount %', 'perc']
            mnth_discount_percentage = mnth_retail_amount and (mnth_discount_amount / mnth_retail_amount) or 0
            ly_mnth_discount_percentage = ly_mnth_retail_amount and (
                    ly_mnth_discount_amount / ly_mnth_retail_amount) or 0
            mnth_discount_inc_dec = ly_mnth_discount_percentage and (
                    mnth_discount_percentage - ly_mnth_discount_percentage) or 0
            yr_discount_percentage = yr_retail_amount and yr_discount_amount / yr_retail_amount or 0
            ly_yr_discount_percentage = ly_yr_retail_amount and ly_yr_discount_amount / ly_yr_retail_amount or 0
            yr_discount_inc_dec = ly_yr_discount_percentage and (
                    yr_discount_percentage - ly_yr_discount_percentage) or 0

            discount_percentage.append(str(round(mnth_discount_percentage * 100, 2)) + '%')
            discount_percentage.append(str(round(ly_mnth_discount_percentage * 100, 2)) + '%')
            discount_percentage.append(str(round(mnth_discount_inc_dec * 100, 2)) + '%')
            discount_percentage.append(str(round(yr_discount_percentage * 100, 2)) + '%')
            discount_percentage.append(str(round(ly_yr_discount_percentage * 100, 2)) + '%')
            discount_percentage.append(str(round(yr_discount_inc_dec * 100, 2)) + '%')

            sales_list.append(retail_sale)
            sales_list.append(discount_amount)
            sales_list.append(discount_percentage)
            sales_list.append(invoice_sale)
            sales_list.append(returned_sale)

            net_sale = self.get_net_sales(invoice_sale, returned_sale)

            sales_list.append(net_sale)
            sales_list.append(gross_margin)
            gross_percentage = self.get_gross_percentage(gross_margin, net_sale)
            sales_list.append(gross_percentage)
        return sales_list

    def get_crm_lines(self, month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                      fiscalyear_start_date, last_yr_fiscalyear_start_date):
        lines = []
        opportunity_no = ['Opportunity #', 'count']
        opportunity_amount = ['Opportunity $', 'amount']
        win_no = ['Won #', 'count']
        win_amount = ['Won $', 'amount']
        lost_no = ['Lost #', 'count']
        lost_amount = ['Lost $', 'amount']

        context = self.env.context
        if 'options' in context:
            customer_ids = self.env['res.partner'].browse(context['options']['partner_ids'])
        else:
            customer_ids = context.get('partner_ids', [])
        if not customer_ids:
            customer_ids = self.env['res.partner'].search([('customer_rank', '>', 0)])

        if customer_ids:
            customer_ids = customer_ids.ids
            customer_ids_str = ','.join(str(x) for x in customer_ids)
            customer_ids = '(' + customer_ids_str + ')'

            opportunity_no, opportunity_amount = self._get_stagewise_crm_lines(False, opportunity_no,
                                                                               opportunity_amount, month_start_date,
                                                                               date_to,
                                                                               last_yr_month_start_date,
                                                                               last_yr_date_to, fiscalyear_start_date,
                                                                               last_yr_fiscalyear_start_date,
                                                                               customer_ids, 'opportunity')[:2]
            # first parameter paased as True for calculate average days
            win_no, win_amount, avg_days_closed = self._get_stagewise_crm_lines(True, win_no, win_amount,
                                                                                month_start_date, date_to,
                                                                                last_yr_month_start_date,
                                                                                last_yr_date_to, fiscalyear_start_date,
                                                                                last_yr_fiscalyear_start_date,
                                                                                customer_ids, 'won')
            lost_no, lost_amount = self._get_stagewise_crm_lines(False, lost_no, lost_amount, month_start_date, date_to,
                                                                 last_yr_month_start_date, last_yr_date_to,
                                                                 fiscalyear_start_date, last_yr_fiscalyear_start_date,
                                                                 customer_ids, 'loss')[:2]
            lines.append(opportunity_no)
            lines.append(opportunity_amount)
            lines.append(win_no)
            lines.append(win_amount)
            lines.append(lost_no)
            lines.append(lost_amount)

            closing_ratio = self.get_closing_ratio(win_no, opportunity_no)
            lines.append(closing_ratio)
            lines.append(avg_days_closed)

        return lines

        # function for format amount into 100,000.00 format(based on

    def format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True).replace(r' ',
                                                                                         u'\N{NO-BREAK SPACE}').replace(
            r'-', u'\u2011')
        return formatted_amount

    # function for updating dollar symbol before amount and change -ve amount to amount in parentheses.
    def update_symbols(self, values):
        list = values[2:]
        new_list = []
        index = [1, 2, 3, 4]
        for x in list:
            if isinstance(x, (float, int)):

                if float(x) < 0.0:
                    new_x = '(' + str(self.format_value(abs(float(x)))) + ')'
                else:
                    new_x = self.format_value(float(x))
            elif isinstance(x, string_types):
                if '%' in x:
                    tmp_x = x.replace("%", "")
                    if float(tmp_x) < 0.0:
                        new_x = '(' + str(self.format_value(abs(float(tmp_x)))) + ')%'
                    else:
                        new_x = str(self.format_value(float(tmp_x))) + '%'
                else:
                    new_x = x
            new_list.append(new_x)
        if values[1] == 'amount':
            for i in index:
                new_list[i - 2] = '$ ' + str(new_list[i - 2])

        final_list = [{'name': k} for k in new_list]
        return final_list

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = []
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format.encode('UTF-8')
        lines = []
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

        fiscalyear_last_date = date_to_obj.replace(month=int(fiscalyear_last_month), day=fiscalyear_last_day)

        if fiscalyear_last_date < date_to_obj:
            fiscalyear_start_date = (fiscalyear_last_date + timedelta(days=1))
        else:
            fiscalyear_start_date = (fiscalyear_last_date + timedelta(days=1)) - relativedelta(years=+1)

        last_yr_fiscalyear_start_date = fiscalyear_start_date - relativedelta(years=1)

        line_id = 0

        # header_col = [
        #     {'name': _('$ TY Sales'), 'class': 'number'},
        #     {'name': _('$ LY Sales'), 'class': 'number'},
        #     {'name': _('Inc/(Dec)'), 'class': 'number'},
        #     {'name': _('YTD'), 'class': 'number'},
        #     {'name': _('LYTD'), 'class': 'number'},
        #     {'name': _('Inc/(Dec)'), 'class': 'number'},
        # ]
        #
        # lines.append({
        #     'id': line_id,
        #     'name': _(''),
        #     'unfoldable': False,
        #     'class': 'o_account_reports_level1',
        #     'columns': header_col,
        #     'title_hover': _('Header'),
        #     'level': 1
        # })
        # line_id += 1

        lines.append({
            'id': line_id,
            'name': 'Sales',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 6)],
            'level': 2,
        })
        line_id += 1
        net_sale_list = []
        gross_margin_list = []

        result_list = self.with_context({'options':options}).get_sale_lines(month_start_date, date_to, last_yr_month_start_date, last_yr_date_to,
                                          fiscalyear_start_date, last_yr_fiscalyear_start_date)
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

        lines.append({
            'id': line_id,
            'name': 'Transactions',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 6)],
            'level': 2,
        })
        line_id += 1

        result_list = self.with_context({'options':options}).get_transaction_lines(net_sale_list, month_start_date, date_to,
                                                 last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                                 last_yr_fiscalyear_start_date)
        for values in result_list:
            list = self.update_symbols(values)
            lines.append({
                'id': line_id,
                'name': values[0],
                'type': 'line',
                'unfoldable': False,
                'columns': list,
                'level': 3,
            })
            line_id += 1

        lines.append({
            'id': line_id,
            'name': 'Repairs',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 6)],
            'level': 2,
        })
        line_id += 1
        result_list =  self.with_context({'options':options}).get_repair_service_lines('Repairs', 'repair', month_start_date, date_to,
                                                    last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                                    last_yr_fiscalyear_start_date)
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

        lines.append({
            'id': line_id,
            'name': 'Services',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 6)],
            'level': 2,
        })
        line_id += 1
        result_list =  self.with_context({'options':options}).get_repair_service_lines('Services', 'service', month_start_date, date_to,
                                                    last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                                    last_yr_fiscalyear_start_date)
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
        lines.append({
            'id': line_id,
            'name': 'CRM',
            'unfoldable': False,
            'columns': [{'name': ''} for k in range(0, 6)],
            'level': 2,
        })
        line_id += 1

        result_list =  self.with_context({'options':options}).get_crm_lines(month_start_date, date_to,
                                         last_yr_month_start_date, last_yr_date_to, fiscalyear_start_date,
                                         last_yr_fiscalyear_start_date)
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

        return [(0, line) for line in lines]
