# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models


class AgentCommissionReport(models.AbstractModel):
    _name = 'agent.commission.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Agent Commission Report Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        lines = []
        context = self.env.context
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        amazon_commission_rate = float(IrConfigParameter.get_param("commission.amazon_commission") or 0.0)

        date_to = context.get('date_to', False)
        if not date_to:
            if options.get('date'):
                date_to = options['date'].get('date_to') or options['date'].get('date')

        date_from = context.get('date_from', False)
        if not date_from:
            if options.get('date') and options['date'].get('date_from'):
                date_from = options['date']['date_from']

        line_id = 0

        allowed_companies = self.env['res.company'].browse(self.env.context.get('allowed_company_ids') or [])

        agent_domain = [('agent', '=', 'True')]
        if options.get('agent') and options.get('agents_ids'):
            agent_domain.append(('id', 'in', options.get('agents_ids')))
        agents = self.env['res.partner'].search(agent_domain)

        amazon_store = self.env['goflow.store'].search([('channel', 'ilike', 'amazon')])
        if amazon_store and amazon_store.ids:
            if len(amazon_store.ids) > 1:
                store_sql = f"invoice.goflow_store_id in {tuple(amazon_store.ids)}"
            else:
                store_sql = f"invoice.goflow_store_id = {amazon_store.ids[0]}"
        else:
            store_sql = 'false'

        sql = f"""
            SELECT 
              invoice.invoice_date AS invoice_date, 
              invoice.name AS invoice_name, 
              rp.name as customer_name, 
              invoice.amount_total - invoice.freight_charges + invoice.discount_total as gross,
              invoice.discount_total as discount,
              invoice.freight_charges as freight_charges,
              case when {store_sql} then (invoice.amount_total - invoice.freight_charges) * {amazon_commission_rate} 
                                        / 100 else 0 end as amazon_commission,
              invoice.amount_total as net_sale,
              case when {store_sql} then invoice.amount_total - invoice.freight_charges - ((invoice.amount_total - 
                                         invoice.freight_charges) * {amazon_commission_rate} / 100) 
                                         else (invoice.amount_total - invoice.freight_charges) end 
                                         as potential_commission_amt,
              case when {store_sql} then (invoice.amount_total - invoice.freight_charges - (
                                        (invoice.amount_total - invoice.freight_charges) * {amazon_commission_rate} 
                                        / 100)) * cmsn.fix_qty / 100 else (invoice.amount_total - 
                                        invoice.freight_charges) * cmsn.fix_qty / 100 end as potential_commission,
              agent.name as agent,
              move.date as date_paid, 
              part.amount as amount_paid,
              case when {store_sql} then (part.amount - ((part.amount/invoice.amount_total)*invoice.freight_charges)) 
                                        - ((part.amount - ((part.amount/invoice.amount_total)*invoice.freight_charges)) 
                                        * {amazon_commission_rate} / 100) else part.amount - (
                                        (part.amount/invoice.amount_total)*invoice.freight_charges) end 
                                        as commissionable_amount,
              cmsn.fix_qty as rate,
              case when {store_sql} then (((part.amount - ((part.amount/invoice.amount_total)*invoice.freight_charges
                                        )) - ((part.amount - ((part.amount/invoice.amount_total) 
                                        * invoice.freight_charges)) * {amazon_commission_rate} / 100)) * cmsn.fix_qty) 
                                        / 100 else ((part.amount - ((part.amount/invoice.amount_total) 
                                        * invoice.freight_charges)) * cmsn.fix_qty) / 100 end as commission
              
            FROM 
              account_payment payment
              JOIN account_move_line line ON line.move_id = move.id 
              JOIN account_partial_reconcile part ON part.debit_move_id = line.id 
              OR part.credit_move_id = line.id 
              JOIN account_move_line counterpart_line ON part.debit_move_id = counterpart_line.id 
              OR part.credit_move_id = counterpart_line.id 
              JOIN account_move invoice ON invoice.id = counterpart_line.move_id 
              left join res_company company on company.id = invoice.company_id
              join res_partner rp on rp.id = invoice.partner_id 
              JOIN account_account account ON account.id = line.account_id 
              join account_invoice_line_agent aila on aila.invoice_id = counterpart_line.move_id 
              join res_partner agent on agent.id = aila.agent_id
              join commission cmsn on cmsn.id = aila.commission_id
            WHERE 
              account.account_type IN ('asset_receivable', 'liability_payable') 
              AND line.id != counterpart_line.id 
              AND invoice.move_type in ('out_invoice') 
              AND move.date >= '{date_from}' 
              AND move.date <= '{date_to}'
        """


        if agents and agents.ids:
            if len(agents.ids) > 1:
                sql += f" AND agent.id in {tuple(agents.ids)} "
            else:
                sql += f" AND agent.id = {agents.ids[0]} "
        else:
            sql += f" and agent.id = 0 "

        if allowed_companies and allowed_companies.ids:
            if len(allowed_companies.ids) > 1:
                sql += f" and company.id in {tuple(allowed_companies.ids)} "
            else:
                sql += f" and company.id = {allowed_companies.ids[0]} "
        else:
            sql += f" and company.id = 0"

        sql += f"""
                GROUP BY move.date, cmsn.fix_qty, aila.commission_id, agent.name, rp.name, payment.id, 
                invoice.move_type, invoice.id, company.name, part.amount 
                ORDER BY agent.name asc, invoice.name, company.name, move.date
            """
        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        agent_list = sorted(list(set([value['agent'] for value in result])))

        for agent in agent_list:
            agent_invoices_lines = []
            invoices_lines = list(filter(lambda line: line['agent'] == agent, result))
            invoice_list = sorted(list(set([value['invoice_name'] for value in invoices_lines])))

            for invoice_id in invoice_list:
                agent_invoice_lines = []
                invoice_lines = list(filter(lambda line: line['invoice_name'] == invoice_id, invoices_lines))
                balance_commission = round(invoice_lines[0]['potential_commission'] or 0.0, 2)

                for invoice in invoice_lines:
                    balance_commission = round(balance_commission - (invoice['commission'] or 0.0), 2)
                    line_column = [
                        {'name': invoice['invoice_date'] or '', 'style': 'text-align:left;'},
                        {'name': invoice['invoice_name'] or '', 'style': 'text-align:left;'},
                        {'name': invoice['customer_name'] or '', 'style': 'text-align:left;'},
                        {'name': '$ {:,.2f}'.format(invoice['gross'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['discount'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['freight_charges'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['amazon_commission'] or 0.0)},
                        {'name': '$ 0.0'},
                        {'name': '$ {:,.2f}'.format(invoice['net_sale'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['potential_commission_amt'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['potential_commission'] or 0.0)},
                        {'name': '-'},
                        {'name': invoice['date_paid'] or '01-01-2020', 'style': 'text-align:left;'},
                        {'name': '$ {:,.2f}'.format(invoice['amount_paid'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['commissionable_amount'] or 0.0)},
                        {'name': str(invoice['rate'] or 0.0) + ' %'},
                        {'name': '$ {:,.2f}'.format(invoice['commission'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(balance_commission or 0.0)},
                    ]
                    agent_invoice_lines.append({
                        'id': line_id,
                        'name': '',
                        'unfoldable': False,
                        'columns': line_column,
                    })
                agent_invoices_lines += agent_invoice_lines
            lines.append({
                'id': line_id,
                'name': agent,
                'unfoldable': False,
                'columns': [],
                'style': 'font-weight:bold !important; border: None;',
                'level': 0,
            })
            lines += agent_invoices_lines
        lines = sorted(lines, key=lambda x: x['id'])
        return [(0, line) for line in lines]
