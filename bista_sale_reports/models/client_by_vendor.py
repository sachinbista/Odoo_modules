# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import pytz

from odoo import models, fields, _


class ClientByCategoryCustomHandler(models.AbstractModel):
    _name = 'client.by.vendor.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Client By Vendor Custom Handler'

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

    # filter_date = {'mode': 'range', 'date_from': '', 'date_to': '', 'filter': 'this_month'}
    # filter_users = True
    # filter_comparison = None
    # filter_partner = True

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
    def get_sale_amount(self, date_from, date_to, salesperson_ids, vendor_id=None, customer_id=None, product_id=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = ("""
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                """)
        user_clause = ''
        # if customer_id:
        #     user_clause = ',so.user_id as user_id'

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
                    %s
                where sp.date_done >= '%s' and sp.date_done <= '%s' 
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                    and sm.product_id = sol.product_id 
                    and sm.state='done'
                    and so.user_id in %s
            """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.partner_id = %s') % (str(vendor_id))

        # if product id is given, add product filter with domain
        if product_id:
            sql += (' and sol.product_id = %s') % (product_id)

        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
            # sql += (' group by so.user_id')

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        cost_price = 0
        invoice_sale = 0
        retail_sale = 0
        product_count = 0
        # user_ids = []
        # serial_number = []
        # so_name = []
        for value in result:
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            retail_sale += value.get('sale_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            # if value.get('user_id', False):
            #     user_ids.append(value.get('user_id', 0))
            # if value.get('serial_number', False):
            #     serial_number.append(value.get('serial_number', 0))
            # if value.get('so_name', False):
            #     so_name.append(value.get('so_name', 0))
        # if customer_id:
        #     return [invoice_sale, retail_sale, product_count,cost_price]
        # else:
        return [invoice_sale, retail_sale, product_count, cost_price]

    def get_sale_amount_for_lot(self, date_from, date_to, salesperson_ids, vendor_id=None, customer_id=None,
                                product_id=None, lot=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = ("""
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                """)
        user_clause = ''
        # if customer_id:
        #     user_clause = ',so.user_id as user_id'
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
                        inner join stock_move_line sml on (sml.move_id = sm.id) 
    					inner join stock_lot sl on (sl.id = sml.lot_id	)
                        %s
                    where sp.date_done >= '%s' and sp.date_done <= '%s' 
                        and sp.state = 'done' and spt.code in ('outgoing', 'incoming')
                        and sm.product_id = sol.product_id
                        and sm.state='done'
                        and so.user_id in %s and sl.name='%s'
                """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids, lot)
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
                                    %s
                                where sp.date_done >= '%s' and sp.date_done <= '%s' 
                                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                                    and sm.product_id = sol.product_id
                                    and sm.state='done'
                                    and so.user_id in %s
                            """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.partner_id = %s') % (str(vendor_id))

        # if product id is given, add product filter with domain
        if product_id:
            sql += (' and sol.product_id = %s') % (product_id)

        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
            # sql += (' group by so.user_id')

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        cost_price = 0
        invoice_sale = 0
        retail_sale = 0
        product_count = 0
        # user_ids = []
        # serial_number = []
        # so_name = []
        for value in result:
            cost_price += value.get('cost_price', 0) or 0
            invoice_sale += value.get('invoice_price', 0) or 0
            retail_sale += value.get('sale_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            # if value.get('user_id', False):
            #     user_ids.append(value.get('user_id', 0))
            # if value.get('serial_number', False):
            #     serial_number.append(value.get('serial_number', 0))
            # if value.get('so_name', False):
            #     so_name.append(value.get('so_name', 0))
        # if customer_id:
        #     return [invoice_sale, retail_sale, product_count,cost_price]
        # else:
        return [invoice_sale, retail_sale, product_count, cost_price]

    def get_sale_amount_of_pos(self, date_from, date_to, salesperson_ids, vendor_id=None, customer_id=None,
                               product_id=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = ("""
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                """)
        user_clause = ''
        # if customer_id:
        #     user_clause = ',he.user_id as user_id'

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
                where sp.date_done >= '%s' and sp.date_done <= '%s'
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = pol.product_id
                    and sm.state='done' 
                    and he.user_id in %s
            """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.partner_id = %s') % (str(vendor_id))

        if product_id:
            sql += (' and pol.product_id = %s' % (product_id))

        # if customer id is given, add customer filter with domain
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        cost_price = 0
        invoice_sale = 0
        retail_sale = 0
        product_count = 0
        # user_ids = []
        for value in result:
            invoice_sale += value.get('invoice_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            retail_sale += value.get('sale_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            # if value.get('user_id', False):
            #     user_ids.append(value.get('user_id', 0))
        # if customer_id:
        #     return [invoice_sale, retail_sale, product_count,cost_price]
        # else:
        return [invoice_sale, retail_sale, product_count, cost_price]

    def get_sale_amount_of_pos_for_lot(self, date_from, date_to, salesperson_ids, vendor_id=None, customer_id=None,
                                       product_id=None, lot=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = ("""
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                """)
        user_clause = ''
        # if customer_id:
        #     user_clause = ',he.user_id as user_id'
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
                           END)* (pol.discount))/100.0 end) as invoice_price 
                        ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) end) as cost_price
                        ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin
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
                        inner join stock_move_line sml on (sml.move_id = sm.id) 
    					inner join stock_lot sl on (sl.id = sml.lot_id	) 
                        %s
                    where sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                        and sm.product_id = pol.product_id
                        and sm.state='done'
                        and he.user_id in %s and sl.name='%s'
                """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids, lot)
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
                                   END)* (pol.discount))/100.0 end) as invoice_price 
                                ,sum(case when pp.std_price= 0.0 then 0 else (pp.std_price * CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                        ELSE 0
                                   END) end) as cost_price
                                ,sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                        WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                        ELSE 0
                                   END) else ((pol.price_unit*sm.product_uom_qty)* (pol.discount))/100.0 end - case when pp.std_price= 0.0 then 0 else (pp.std_price * sm.product_uom_qty) end)  as gross_margin
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
                            where sp.date_done >= '%s' and sp.date_done <= '%s'
                                and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                                and sm.product_id = pol.product_id
                                and sm.state='done'
                                and he.user_id in %s
                        """) % (user_clause, product_join_clause, date_from, date_to, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.partner_id = %s') % (str(vendor_id))

        if product_id:
            sql += (' and pol.product_id = %s' % (product_id))

        # if customer id is given, add customer filter with domain
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)

        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        cost_price = 0
        invoice_sale = 0
        retail_sale = 0
        product_count = 0
        # user_ids = []
        for value in result:
            invoice_sale += value.get('invoice_price', 0) or 0
            cost_price += value.get('cost_price', 0) or 0
            retail_sale += value.get('sale_price', 0) or 0
            product_count += value.get('net_qty', 0) or 0
            # if value.get('user_id', False):
            #     user_ids.append(value.get('user_id', 0))
        # if customer_id:
        #     return [invoice_sale, retail_sale, product_count,cost_price]
        # else:
        return [invoice_sale, retail_sale, product_count, cost_price]

    def get_customer_ids(self, date_from, date_to, salesperson_ids, vendor_id):
        sql = ("""
                SELECT sum(invoice_price) as customer_sum, ss.partner_id as partner_id 
                FROM (
                (
                    SELECT 
                        sum(case when pol.discount = 0.0 then (pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
                                WHEN spt.code in ('incoming') THEN -(sm.product_uom_qty)
                                ELSE 0
                           END) else ((pol.price_unit*CASE WHEN spt.code in ('outgoing') THEN (sm.product_uom_qty)
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
                    WHERE sp.date_done >= '%s' and sp.date_done <= '%s'
                        and sp.state = 'done' and spt.code in ('outgoing','incoming') 
                        and sm.product_id = pol.product_id
                        and sm.state='done'
                        and he.user_id in %s and psi.partner_id = %s 
                        and pt.exclude_FROM_report!=True 
                        group by rp.id
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
                    WHERE sp.date_done >= '%s' and sp.date_done <= '%s'  
                        and sp.state = 'done' and spt.code in ('outgoing','incoming') 
                        and sm.product_id = sol.product_id 
                        and sm.state='done'
                        and pt.exclude_FROM_report!=True and psi.partner_id = %s and so.user_id in %s group by rp.id
                ))
                 ss group by partner_id order by customer_sum desc
            """) % (date_from, date_to, salesperson_ids, vendor_id, date_from, date_to, vendor_id, salesperson_ids)
        self._cr.execute(sql)
        res = self._cr.fetchall()
        customer_ids = []
        for id in res:
            customer_ids.append(id[1])
        return customer_ids

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

    def get_product_owner(self, product_id):
        # owner_id =self.env.user.company_id.partner_id
        owner_id = 'O'
        quants = self.env['stock.quant'].search([('product_id', '=', product_id), ('owner_id', '!=', False)], limit=1)
        if quants:
            owner_id = 'M'

        return owner_id

    def get_product_ids(self, date_from, date_to, salesperson_ids, vendor_id=None, customer_id=None):
        product_join_clause = ''
        if vendor_id:
            product_join_clause = ("""
                    inner join product_supplierinfo psi on(pt.id = psi.product_tmpl_id)
                """)

        sql = ("""
                select 
                    pp.id
                from sale_order_line sol
                    inner join sale_order so on (so.id = sol.order_id)
                    inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
                    inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
                    inner join stock_move sm on (sp.id = sm.picking_id)
                    inner join res_partner rp on (rp.id = so.partner_id)
                    inner join product_product pp on (sol.product_id = pp.id)
                    INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                    FULL OUTER join res_users_sale_order_rel usrso on (usrso.sale_order_id=so.id)
                    %s
                where sp.date_done >= '%s' and sp.date_done <= '%s' 
                    and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                    and sm.product_id = sol.product_id
                    and sm.state='done'
                    and (so.user_id in %s or usrso.res_users_id in %s) 
            """) % (product_join_clause, date_from, date_to, salesperson_ids, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.partner_id = %s') % (str(vendor_id))

        # if customer id is given, add customer filter with domain
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
        sale_product_ids = []
        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            if id[0] not in sale_product_ids:
                sale_product_ids += id
        sql = ("""
                        select 
                            pp.id
                        from pos_order_line pol
                            inner join pos_order po ON (po.id = pol.order_id)
                            inner join stock_picking sp on (sp.pos_order_id = po.id)
                        INNER JOIN stock_picking_type spt ON (spt.id = sp.picking_type_id)
                        INNER JOIN stock_move sm ON (sp.id = sm.picking_id)
                        INNER JOIN res_partner rp ON (rp.id = po.partner_id)
                        INNER JOIN product_product pp ON (sm.product_id = pp.id)
                        INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id) 
                        INNER JOIN hr_employee he on (he.id = po.employee_id)
                        FULL OUTER JOIN pos_order_res_users_rel posusr on (posusr.pos_order_id = po.id)
                            %s
                        where sp.date_done >= '%s' and sp.date_done <= '%s' 
                            and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                            and sm.product_id = pol.product_id
                            and sm.state='done' 
                            and (he.user_id in %s  or posusr.res_users_id in %s)
                    """) % (product_join_clause, date_from, date_to, salesperson_ids, salesperson_ids)

        # if vender is given, add vender filter with the domain
        if vendor_id:
            sql += (' and psi.partner_id = %s') % (str(vendor_id))

        # if customer id is given, add customer filter with domain
        if customer_id:
            sql += (' and rp.id = %s') % (customer_id)
        pos_product_ids = []
        self._cr.execute(sql)
        res = self._cr.fetchall()
        for id in res:
            if id[0] not in pos_product_ids:
                pos_product_ids += id
        return sale_product_ids, pos_product_ids

    def get_sn_sp_dn_of_so(self, date_from, date_to, product_id=None, customer_id=None):
        if product_id:
            sql1 = ("""
        			select
        				sl.name as serial_number,so.name as so_name,COALESCE(rp.short_code, rp.name) as salesperson
        			from sale_order_line sol
        				inner join sale_order so on (so.id = sol.order_id)
        				inner join stock_picking sp on (sp.group_id = so.procurement_group_id)
        				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
        				inner join stock_move sm on (sp.id = sm.picking_id)
        				inner join stock_move_line sml on (sml.move_id = sm.id) 
        				left join stock_lot sl on (sl.id = sml.lot_id	)
        				left join res_users ru on (ru.id = so.user_id)
    			 		left join res_partner rp on (rp.id = ru.partner_id)
        			where sp.date_done >= '%s' and sp.date_done <= '%s' 
        				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                        and sm.product_id = sol.product_id
                        and sm.state='done' 
                        and so.partner_id = %s 
        			""") % (date_from, date_to, customer_id)
            sql1 += ('and sol.product_id = %s ' % (product_id))
            self._cr.execute(sql1)
            result1 = self._cr.dictfetchall()
            serial_number = []
            salesperson = []
            so_name = []
            for value in result1:
                serial_number.append(value.get('serial_number', '') or '')
                salesperson.append(value.get('salesperson', '') or '')
                so_name.append(value.get('so_name', '') or '')
            serial_number = list(set(serial_number))
            salesperson = list(set(salesperson))
            so_name = list(set(so_name))
        return [serial_number, salesperson, so_name]

    def get_sn_sp_dn_of_pos(self, date_from, date_to, product_id=None, customer_id=None):
        if product_id:
            sql1 = ("""
        			select 
        				sl.name as serial_number,po.name as po_name,po.cashier as salesperson
        			from pos_order_line pol
        				inner join pos_order po on (po.id = pol.order_id)
        				inner join stock_picking sp on (sp.pos_order_id = po.id)
        				inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
        				inner join stock_move sm on (sp.id = sm.picking_id)
        				inner join stock_move_line sml on (sml.move_id = sm.id)
        				left join stock_lot sl on (sl.id = sml.lot_id	)
        			where sp.date_done >= '%s' and sp.date_done <= '%s' 
        				and sp.state = 'done' and spt.code in ('outgoing', 'incoming') 
                        and sm.product_id = pol.product_id
                        and sm.state='done' 
                        and po.partner_id = %s
        			""") % (date_from, date_to, customer_id)
            sql1 += ('and pol.product_id = %s' % (product_id))
            # sql2 = ("""
            # 	select
            # 		po.cashier as salesperson
            # 	from pos_order_line pol
            # 		inner join pos_order po on (po.id = pol.order_id)
            # 		inner join stock_picking sp on (sp.pos_order_id = po.id)
            # 		inner join stock_picking_type spt on (spt.id = sp.picking_type_id)
            # 		inner join stock_move sm on (sp.id = sm.picking_id)
            # 	where sp.date_done >= '%s' and sp.date_done <= '%s'
            # 		and sp.state = 'done' and spt.code in ('outgoing', 'incoming') and sm.product_id = pol.product_id
            # 	""") % (date_from, date_to)
            # sql2 += ('and pol.product_id = %s' % (product_id))
            self._cr.execute(sql1)
            result1 = self._cr.dictfetchall()
            # self._cr.execute(sql2)
            # result2 = self._cr.dictfetchall()
            serial_number = []
            salesperson = []
            po_name = []
            for value in result1:
                serial_number.append(value.get('serial_number', '') or '')
                salesperson.append(value.get('salesperson', '') or '')
                po_name.append(value.get('po_name', '') or '')
            serial_number = list(set(serial_number))
            salesperson = list(set(salesperson))
            po_name = list(set(po_name))
        # for value in result2:
        # 	salesperson.append(value.get('salesperson', '') or '')
        return [serial_number, salesperson, po_name]

    def get_sn_sp_all(self, options, product, customer, vendor):
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

        serial_numbers = []

        for period in periods:
            period_date_from = period.get('date_from')
            period_date_to = period.get('date_to')
            sn_sp_so = self.get_sn_sp_dn_of_so(period_date_from, period_date_to, product_id=product.id,
                                               customer_id=customer.id)
            sn_sp_pos = self.get_sn_sp_dn_of_pos(period_date_from, period_date_to, product_id=product.id,
                                                 customer_id=customer.id)
            serial_numbers_all = sn_sp_so[0] + sn_sp_pos[0]
            salesperson_all = list(set(sn_sp_so[1] + sn_sp_pos[1]))
            sales_name_all = sn_sp_so[2] + sn_sp_pos[2]
            serial_numbers.append({product.id: [serial_numbers_all, salesperson_all, sales_name_all]})
        # salespersons.append({product.id: salesperson_all})
        return serial_numbers

    def get_vendor_reference(self, product):
        ref = ''
        if product:
            for pricelist in product.seller_ids:
                if pricelist.product_code:
                    ref = pricelist.product_code
                    break
        return ref

    def dollar_format_value(self, value):
        fmt = '%.2f'
        lang_code = self._context.get('lang') or 'en_US'
        lang = self.env['res.lang']._lang_get(lang_code)
        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True).replace(r' ',
                                                                                         u'\N{NO-BREAK SPACE}').replace(
            r'-', u'\u2011')
        formatted_amount = "$ {}".format(formatted_amount[:formatted_amount.find('.')])
        return formatted_amount

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

        periods = options.get('comparison', False) and options.get('comparison', False).get('periods') or []
        periods_vals = {'string': 'initial', 'date_from': date_from, 'date_to': date_to}

        if not periods:
            periods.append(periods_vals)
        else:
            periods.insert(0, periods_vals)

        vendor_header = [
            # {'name': _('Street , City, State Zip'), 'colspan': 3, 'class': 'text-left'},
            # {'name': _('Email'), 'colspan': 1, 'class': 'text-left'},
            # {'name': _('Phone'), 'colspan': 1, 'class': 'text-left'},
            # {'name': _('Mobile'), 'colspan': 1, 'class': 'text-left'},
            # {'name': _('Qty'), 'class': 'number', 'colspan': 1},
            # {'name': _('Retail'), 'class': 'number', 'colspan': 1},
            # {'name': _('Sales'), 'class': 'number', 'colspan': 1},
            # {'name': _('Disc%'), 'class': 'number', 'colspan': 1},
            # {'name': _('COGS'), 'class': 'number', 'colspan': 1},
            # {'name': _('GM$'), 'class': 'number', 'colspan': 1},
            # {'name': _('GM%'), 'class': 'number', 'colspan': 1},
        ]
        lines.append({
            'id': line_id,
            'name': 'Vendor',
            'unfoldable': False,
            'columns': vendor_header,
            'style': 'font-weight:bold !important; border: None;'
        })
        line_id += 1

        cust_header = [
            {'name': _('Street , City, State Zip'), 'colspan': 3, 'class': 'text-left'},
            {'name': _('Email'), 'colspan': 1, 'class': 'text-left'},
            {'name': _('Phone'), 'colspan': 1, 'class': 'text-left'},
            {'name': _('Mobile'), 'colspan': 1, 'class': 'text-left'},
            # {'name': _('Qty'), 'class': 'number', 'colspan': 1},
            # {'name': _('Retail'), 'class': 'number', 'colspan': 1},
            # {'name': _('Sales'), 'class': 'number', 'colspan': 1},
            # {'name': _('Disc%'), 'class': 'number', 'colspan': 1},
            # {'name': _('COGS'), 'class': 'number', 'colspan': 1},
            # {'name': _('GM$'), 'class': 'number', 'colspan': 1},
            # {'name': _('GM%'), 'class': 'number', 'colspan': 1},
        ]
        lines.append({
            'id': line_id,
            'name': 'Client',
            'unfoldable': False,
            'columns': cust_header,
            'style': 'font-weight:bold !important; border: None;',
            'level': 2,
        })
        line_id += 1

        ## Add header to sub lines :::
        sub_header = [
            {'name': _('Product Name'), 'class': 'text-left', 'colspan': 3},
            {'name': _('Serial #'), 'class': 'text-left', 'colspan': 1},
            {'name': _('Document #'), 'class': 'text-left', 'colspan': 1},
            {'name': _('SP'), 'class': 'text-left', 'colspan': 1},
            {'name': _('Qty'), 'class': 'number', 'colspan': 1},
            {'name': _('Retail'), 'class': 'number', 'colspan': 1},
            {'name': _('Sales'), 'class': 'number', 'colspan': 1},
            {'name': _('Disc%'), 'class': 'number', 'colspan': 1},
            {'name': _('COGS'), 'class': 'number', 'colspan': 1},
            {'name': _('GM$'), 'class': 'number', 'colspan': 1},
            {'name': _('GM%'), 'class': 'number', 'colspan': 1},
        ]
        lines.append({
            'id': line_id,
            'name': 'Int Ref',
            'unfoldable': False,
            'columns': sub_header,
            'level': 3,
            'style': 'font-weight:bold !important; border: None;',
        })
        line_id += 1

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

        # called function to find the total ssale for the period
        # total_invoice_sale, total_discount, total_product_count = self.get_sale_amount(date_from, date_to,salesperson_ids)
        # total_invoice_sale_pos, total_discount_pos, total_product_count_pos = self.get_sale_amount_of_pos(date_from,
        #                                                                                                   date_to,
        #                                                                                                   salesperson_ids)
        # total_invoice_sale = total_invoice_sale + total_invoice_sale_pos
        # sale_perc_sum = 0
        # invoice_sale_sum = {}
        # product_count_sum = {}
        # retail_sale_sum = {}
        # current_period_customer_ids = []
        # current_vendor_invoice_sale = 0
        # periods = self.remove_duplicated_period(periods)
        # # initialize dictionary variable with zero based on periods
        # for period in periods:
        #     period_date_from = self.get_date_with_tz(str(period.get('date_from')) + ' 00:00:00')
        #     invoice_sale_sum[period_date_from] = 0
        #     product_count_sum[period_date_from] = 0
        #     retail_sale_sum[period_date_from] = 0
        # iterate with vendor ids
        vendor_ids = self.env['res.partner'].browse(options.get('partner_ids', []))

        if not vendor_ids:
            vendor_ids = self.env['res.partner'].search([('supplier_rank', '>', 0)])
        total_product_count = 0
        total_product_retail = 0
        total_product_invoice_amount = 0
        total_product_cost_amount = 0
        total_gross_margin = 0
        for vendor in vendor_ids:
            # called function to get vendor wise sum and vendor wise customer details
            vendor_invoice_sale, vendor_retail_sale, vendor_product_count, vendor_cost_price = self.get_sale_amount(
                date_from,
                date_to,
                salesperson_ids,
                vendor_id=vendor.id)
            vendor_invoice_sale_pos, vendor_retail_sale_pos, vendor_product_count_pos, vendor_cost_price = self.get_sale_amount_of_pos(
                date_from, date_to, salesperson_ids, vendor_id=vendor.id)
            vendor_invoice_sale = vendor_invoice_sale + vendor_invoice_sale_pos
            if not vendor_invoice_sale:
                continue
            current_period_customer_ids = self.get_customer_ids(date_from, date_to, salesperson_ids, vendor.id)
            contact_address = ''
            if vendor.street:
                contact_address += vendor.street + ', '
            if vendor.city:
                contact_address += vendor.city + ', '
            if vendor.state_id:
                contact_address += vendor.state_id.name
            if vendor.zip:
                contact_address += ' - ' + vendor.zip

            contact_email = ''
            if vendor.email:
                contact_email += self.split_multi_emails(vendor.email, ';')
            vendor_address_column = [{'name': contact_address, 'colspan': 3, 'class': 'text-left'},
                                     {'name': contact_email, 'colspan': 1, 'class': 'text-left'},
                                     {'name': vendor.phone or '', 'colspan': 1, 'class': 'text-left'},
                                     {'name': vendor.mobile or '', 'colspan': 1, 'class': 'text-left'}]
            vendor_line_id = line_id
            line_id += 1
            vendor_product_count = 0
            vendor_product_retail = 0
            vendor_product_invoice_amount = 0
            vendor_product_cost_amount = 0
            vendor_gross_margin = 0


            for customer in self.env['res.partner'].browse(current_period_customer_ids):

                sale_product_ids, pos_product_ids = self.get_product_ids(date_from, date_to, salesperson_ids,
                                                                         vendor_id=vendor.id, customer_id=customer.id)
                if not sale_product_ids and not pos_product_ids:
                    continue
                if sale_product_ids or pos_product_ids:
                    customer_product_count = 0
                    customer_product_retail = 0
                    customer_product_invoice_amount = 0
                    customer_product_cost_amount = 0
                    customer_gross_margin = 0
                    contact_address = ''
                    if customer.street:
                        contact_address += customer.street + ', '
                    if customer.city:
                        contact_address += customer.city + ', '
                    if customer.state_id:
                        contact_address += customer.state_id.name
                    if customer.zip:
                        contact_address += ' - ' + customer.zip

                    contact_email = ''
                    if customer.email:
                        contact_email += self.split_multi_emails(customer.email, ';')
                    customer_address_column = [{'name': contact_address, 'colspan': 3, 'class': 'text-left'},
                                               {'name': contact_email, 'colspan': 1, 'class': 'text-left'},
                                               {'name': customer.phone or '', 'colspan': 1, 'class': 'text-left'},
                                               {'name': customer.mobile or '', 'colspan': 1, 'class': 'text-left'}]
                    customer_line_id = line_id
                    line_id += 1
                    sale_product_ids.extend(pos_product_ids)

                    for product in self.env['product.product'].browse(sale_product_ids):

                        owner = self.get_product_owner(product_id=product.id)

                        def insert_newline(string, index, addin):
                            return string[:index] + addin + string[index:]

                        product_name = product.name[:30] or product.name

                        product_sale_amount_list = self.get_sale_amount(date_from, date_to, salesperson_ids,
                                                                        vendor_id=vendor.id, customer_id=customer.id,
                                                                        product_id=product.id)
                        product_sale_amount_list_pos = self.get_sale_amount_of_pos(date_from, date_to, salesperson_ids,
                                                                                   vendor_id=vendor.id,
                                                                                   customer_id=customer.id,
                                                                                   product_id=product.id)
                        product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                      product_sale_amount_list_pos[0]
                        product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                      product_sale_amount_list_pos[1]
                        product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                      product_sale_amount_list_pos[2]
                        product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                      product_sale_amount_list_pos[3]
                        product_cost_amount = product_sale_amount_list[3]
                        product_invoice_amount = product_sale_amount_list[0]
                        product_retail_sale = product_sale_amount_list[1]
                        product_product_count = product_sale_amount_list[2]
                        if not product_product_count:
                            continue
                        sn_sp_all = self.get_sn_sp_all(options, product, customer, vendor)
                        has_lots = False
                        for line in sn_sp_all:
                            if has_lots:
                                break
                            for key, val in line.items():
                                if key == product.id and len(val[0]) > 1:
                                    has_lots = True
                                    break
                        if not has_lots:
                            customer_product_count += product_product_count
                            vendor_product_count += product_product_count
                            customer_product_retail += (product.lst_price * int(product_product_count))
                            vendor_product_retail += (product.lst_price * int(product_product_count))

                            customer_product_invoice_amount += product_invoice_amount
                            vendor_product_invoice_amount += product_invoice_amount
                            product_discount = product_retail_sale and (
                                    product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                            product_discount_perc = str(
                                self.format_value(round(product_discount * 100, 2))) + '%'
                            gross_margin = product_invoice_amount - product_cost_amount
                            gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                            gross_margin_perc = str(self.format_value(round(gross_margin_perc * 100, 2))) + '%'
                            customer_product_cost_amount += product_cost_amount
                            vendor_product_cost_amount += product_cost_amount
                            customer_gross_margin += gross_margin
                            vendor_gross_margin += gross_margin
                            column = [
                                {'name': product_name, 'colspan': 3},
                                {'name': ''},
                                {'name': ''},
                                {'name': ''},
                                {'name': int(product_product_count), 'class': 'text-right'},
                                {'name': self.dollar_format_value(product.lst_price * int(product_product_count))},
                                {'name': self.dollar_format_value(product_invoice_amount)},
                                {'name': product_discount_perc},
                                {'name': self.dollar_format_value(product_cost_amount)},
                                {'name': self.dollar_format_value(gross_margin)},
                                {'name': gross_margin_perc}]
                            for line in sn_sp_all:
                                for key, val in line.items():
                                    if len(val[0]) == 1:
                                        column[1].update({'name': val[0][0]})
                                    if len(val[1]) == 1:
                                        column[3].update({'name': val[1][0]})
                                    if len(val[2]) == 1:
                                        column[2].update({'name': val[2][0]})
                                    if len(val[1]) > 1:
                                        column[3].update({'name': ",".join(val[1])})
                                    if len(val[0]) > 1:
                                        column[1].update({'name': ",".join(val[0])})
                                    if len(val[2]) > 1:
                                        column[2].update({'name': ",".join(val[2])})

                            lines.append({
                                'id': line_id,
                                'name': product.default_code and product.default_code or '',
                                'unfoldable': False,
                                'class': 'text-left',
                                'columns': column,
                                'level': 3,
                                'style': 'font-weight:400 !important'
                            })
                            line_id += 1
                        else:
                            for line in sn_sp_all:
                                for key, val in line.items():
                                    if key == product.id and len(val[0]) > 1:
                                        for data in val[0]:
                                            product_sale_amount_list = self.get_sale_amount_for_lot(
                                                date_from,
                                                date_to, salesperson_ids,
                                                vendor_id=vendor.id,
                                                customer_id=customer.id,
                                                product_id=product.id, lot=data)
                                            product_sale_amount_list_pos = self.get_sale_amount_of_pos_for_lot(
                                                date_from,
                                                date_to, salesperson_ids,
                                                vendor_id=vendor.id,
                                                customer_id=customer.id,
                                                product_id=product.id, lot=data)
                                            product_sale_amount_list[0] = product_sale_amount_list[0] + \
                                                                          product_sale_amount_list_pos[0]
                                            product_sale_amount_list[1] = product_sale_amount_list[1] + \
                                                                          product_sale_amount_list_pos[1]
                                            product_sale_amount_list[2] = product_sale_amount_list[2] + \
                                                                          product_sale_amount_list_pos[2]
                                            product_sale_amount_list[3] = product_sale_amount_list[3] + \
                                                                          product_sale_amount_list_pos[3]
                                            product_cost_amount = product_sale_amount_list[3]
                                            product_invoice_amount = product_sale_amount_list[0]
                                            product_retail_sale = product_sale_amount_list[1]
                                            product_product_count = product_sale_amount_list[2]
                                            if not product_product_count:
                                                continue
                                            customer_product_count += product_product_count
                                            vendor_product_count += product_product_count
                                            customer_product_retail += (product.lst_price * int(product_product_count))
                                            vendor_product_retail += (product.lst_price * int(product_product_count))

                                            customer_product_invoice_amount += product_invoice_amount
                                            vendor_product_invoice_amount += product_invoice_amount
                                            product_discount = product_retail_sale and (
                                                    product_retail_sale - product_invoice_amount) / product_retail_sale or 0
                                            product_discount_perc = str(
                                                self.format_value(round(product_discount * 100, 2))) + '%'
                                            gross_margin = product_invoice_amount - product_cost_amount
                                            gross_margin_perc = product_invoice_amount and gross_margin / product_invoice_amount or 0
                                            gross_margin_perc = str(
                                                self.format_value(round(gross_margin_perc * 100, 2))) + '%'
                                            customer_product_cost_amount += product_cost_amount
                                            vendor_product_cost_amount += product_cost_amount
                                            customer_gross_margin += gross_margin
                                            vendor_gross_margin += gross_margin
                                            column = [
                                                {'name': product_name, 'colspan': 3},
                                                {'name': ''},
                                                {'name': '', 'colspan': 1},
                                                {'name': ''},
                                                {'name': int(product_product_count), 'class': 'text-right'},
                                                {'name': self.dollar_format_value(
                                                    product.lst_price * int(product_product_count))},
                                                {'name': self.dollar_format_value(product_invoice_amount)},
                                                {'name': product_discount_perc},
                                                {'name': self.dollar_format_value(product_cost_amount)},
                                                {'name': self.dollar_format_value(gross_margin)},
                                                {'name': gross_margin_perc}
                                            ]
                                            for line in sn_sp_all:
                                                for key, val in line.items():
                                                    if len(val[1]) == 1:
                                                        column[3].update({'name': val[1][0]})
                                                    if len(val[1]) > 1:
                                                        column[3].update({'name': ",".join(val[1])})
                                                    if len(val[2]) == 1:
                                                        column[2].update({'name': val[2][0]})
                                                    if len(val[2]) > 1:
                                                        column[2].update({'name': ",".join(val[2])})
                                            column[1].update({'name': data})
                                            lines.append({
                                                'id': line_id,
                                                'name': product.default_code and product.default_code or '',
                                                'unfoldable': False,
                                                'columns': column,
                                                'level': 2,
                                            })
                                            line_id += 1
                    if customer_product_count:
                        product_discount = customer_product_retail and (
                                customer_product_retail - customer_product_invoice_amount) / customer_product_retail or 0
                        product_discount_perc = str(
                            self.format_value(round(product_discount * 100, 2))) + '%'
                        gross_margin = customer_product_invoice_amount - customer_product_cost_amount
                        gross_margin_perc = customer_product_invoice_amount and gross_margin / customer_product_invoice_amount or 0
                        gross_margin_perc = str(self.format_value(round(gross_margin_perc * 100, 2))) + '%'
                        customer_address_column += [
                            {'name': int(customer_product_count), 'class': 'text-right'},
                            {'name': self.dollar_format_value(customer_product_retail)},
                            {'name': self.dollar_format_value(customer_product_invoice_amount)},
                            {'name': product_discount_perc},
                            {'name': self.dollar_format_value(customer_product_cost_amount)},
                            {'name': self.dollar_format_value(customer_gross_margin)},
                            {'name': gross_margin_perc}, ]
                        lines.append({
                            'id': customer_line_id,
                            'name': str(customer.name or customer.parent_name or ' '),
                            'unfoldable': False,
                            'columns': customer_address_column,
                            'level': 2,
                            'style': 'font-weight:bold !important'

                        })
            line_id += 1
            lines.append({
                'id': line_id,
                'name': ' ',
                'columns': [{'name': ' '}],
                'unfoldable': False,
            })
            total_product_count += vendor_product_count
            total_product_retail += vendor_product_retail
            total_product_invoice_amount += vendor_product_invoice_amount
            total_product_cost_amount += vendor_product_cost_amount
            total_gross_margin += vendor_gross_margin
            product_discount = vendor_product_retail and (
                    vendor_product_retail - vendor_product_invoice_amount) / vendor_product_retail or 0
            product_discount_perc = str(
                self.format_value(round(product_discount * 100, 2))) + '%'
            gross_margin = vendor_product_invoice_amount - vendor_product_cost_amount
            gross_margin_perc = vendor_product_invoice_amount and gross_margin / vendor_product_invoice_amount or 0
            gross_margin_perc = str(self.format_value(round(gross_margin_perc * 100, 2))) + '%'
            vendor_address_column += [
                {'name': int(vendor_product_count), 'class': 'text-right'},
                {'name': self.dollar_format_value(vendor_product_retail)},
                {'name': self.dollar_format_value(vendor_product_invoice_amount)},
                {'name': product_discount_perc},
                {'name': self.dollar_format_value(vendor_product_cost_amount)},
                {'name': self.dollar_format_value(vendor_gross_margin)},
                {'name': gross_margin_perc}, ]
            vendor_line = {
                'id': vendor_line_id,
                'name': str(vendor.name_get()[0][1] or ' '),
                'columns': vendor_address_column,
                'unfoldable': False,
                'style': 'font-weight:bolder'
            }
            if vendor_line_id != 0:
                vendor_line['page_break'] = True
            lines.append(vendor_line)
        product_discount = total_product_retail and (
                total_product_retail - total_product_invoice_amount) / total_product_retail or 0
        product_discount_perc = str(
            self.format_value(round(product_discount * 100, 2))) + '%'
        gross_margin = total_product_invoice_amount - total_product_cost_amount
        gross_margin_perc = total_product_invoice_amount and gross_margin / total_product_invoice_amount or 0
        gross_margin_perc = str(self.format_value(round(gross_margin_perc * 100, 2))) + '%'
        total_column = [
            {'name': '', 'colspan': 3},
            {'name': ''},
            {'name': ''},
            {'name': ''},
            {'name': int(total_product_count), 'class': 'text-right'},
            {'name': self.dollar_format_value(total_product_retail)},
            {'name': self.dollar_format_value(total_product_invoice_amount)},
            {'name': product_discount_perc},
            {'name': self.dollar_format_value(total_product_cost_amount)},
            {'name': self.dollar_format_value(total_gross_margin)},
            {'name': gross_margin_perc}, ]
        lines.append({
            'id': line_id + 1,
            'name': 'Total',
            'columns': total_column,
            'unfoldable': False,
            'style': 'font-weight:bold'
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
