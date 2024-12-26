from odoo import api, fields, models, _
import xlwt
from io import BytesIO
import base64
from datetime import datetime
from odoo.exceptions import ValidationError,UserError
import logging


class ViewReport(models.TransientModel):
    _name = "view.report"
    _description = "View Report"

    file = fields.Binary('File',readonly=True)
    file_name = fields.Char('File Name',readonly=True)

class agent_commission_report_wizard(models.TransientModel):
    _name = "agent.commission.report.wizard"
    _description = "Agent Commision Report"

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    commission_agent_ids = fields.Many2many('res.partner',
            string='Agents',
            domain=[('agent', '=', True)])

    def generate_agent_commission_report(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("""Start Date cannot be bigger than End Date."""))
        self.env.cr.execute("delete from agent_commission_reports")
        allowed_companies = self.env['res.company'].browse(self.env.context.get('allowed_company_ids') or [])
        agents = False
        date_start = self.start_date
        date_end = self.end_date
        if self.commission_agent_ids:
            agents = self.commission_agent_ids
        else:
            agents = self.env['res.partner'].search([('agent', '=', True)])
        if agents and agents.ids:
            if len(agents.ids) > 1:
                agents = f" AND agent.agent_id in {tuple(agents.ids)} "
            else:
                agents = f" AND agent.agent_id = {agents.ids[0]} "
        else:
            agents = f" AND agent.agent_id = 0 "
        if allowed_companies and allowed_companies.ids:
            if len(allowed_companies.ids) > 1:
                allowed_companies = f" AND invoice.company_id in {tuple(allowed_companies.ids)} "
            else:
                allowed_companies = f" AND invoice.company_id = {allowed_companies.ids[0]} "
        else:
            allowed_companies = f" AND invoice.company_id = 0"

        query = f"""WITH payments as (select invoice_payments.part_id as part_id,invoice_payments.invoice_id as invoice_id,invoice_payments.max_date as max_date from ((select 
            invoice.id as invoice_id,
            CAST(full_rec.create_date AS DATE) as max_date,
            part.id as part_id
            
        from account_invoice_line_agent as agent 
        left join account_move as invoice on invoice.id = agent.invoice_id 
        left join account_move_line line on line.move_id = invoice.id

        JOIN account_partial_reconcile part ON
            part.debit_move_id = line.id
            OR
            part.credit_move_id = line.id

        JOIN account_full_reconcile full_rec ON
            full_rec.id = part.full_reconcile_id

        JOIN account_move_line in_move_line on 
            part.credit_move_id = in_move_line.id
        JOIN account_move in_move on 
            in_move_line.move_id = in_move.id
        JOIN account_account in_account on
            in_account.id = in_move_line.account_id

        where 
            in_account.account_type IN ('asset_receivable', 'liability_payable')
            AND invoice.move_type in ('out_invoice','out_refund')
            AND agent.rate > 0
            AND CAST(full_rec.create_date AS DATE) IS NOT NULL                                                                                                                                                  
            AND part.max_date <= '{date_end}' AND agent.agent_id = 17619  AND invoice.company_id = 2 
            group by invoice.id,part.id,full_rec.create_date
            order by
                invoice.id)

            UNION

            (select 
            invoice.id as invoice_id,
            CASE 
                    WHEN full_rec.create_date IS NOT NULL THEN CAST(full_rec.create_date AS DATE) 
                    ELSE NULL
                END AS max_date,
            part.id as part_id
            
        from account_invoice_line_agent as agent 
        left join account_move as invoice on invoice.id = agent.invoice_id 
        left join account_move_line line on line.move_id = invoice.id

        JOIN account_partial_reconcile part ON
            part.debit_move_id = line.id
            OR
            part.credit_move_id = line.id

        FULL OUTER JOIN account_full_reconcile full_rec ON
            full_rec.id = part.full_reconcile_id

        JOIN account_move_line in_move_line on 
            part.credit_move_id = in_move_line.id
        JOIN account_move in_move on 
            in_move_line.move_id = in_move.id
        JOIN account_account in_account on
            in_account.id = in_move_line.account_id

        where 
            in_account.account_type IN ('asset_receivable', 'liability_payable')
            AND invoice.move_type in ('out_invoice','out_refund')
            AND agent.rate > 0
            
            AND part.max_date <= '{date_end}'"""
        query += agents
        query += allowed_companies
        query += f"""
            group by invoice.id,part.id,full_rec.create_date
            order by
                invoice.id)) as invoice_payments group by invoice_payments.invoice_id,invoice_payments.part_id,invoice_payments.max_date)
                """
        query += f"""
        (select 
            coalesce(agent.agent_id) AS agent_id,
            invoice.date AS invoiced_date,
            invoice.id AS invoice_id,
            customer.name as customer_name,
            invoice.partner_id AS partner_id,
            round(coalesce(invoice.amount_total - invoice.freight_charges + invoice.discount_total,0.00)::numeric,2) as gross,
            round(coalesce(invoice.discount_total,0.00)::numeric,2) as discount,
            round(coalesce(invoice.freight_charges,0.00)::numeric,2) as freight_charges,
            round(coalesce(invoice.amazon_commission,0.00)::numeric,2) as amazon_charges,
            round(coalesce(invoice.amount_total,0.00)::numeric,2) as net_sale,
            round(coalesce(coalesce(invoice.amount_total,0.00) - coalesce(invoice.freight_charges,0.00) - coalesce(invoice.amazon_commission,0.00),0.00)::numeric,2) as potential_commission_amt,
            round(coalesce((coalesce(invoice.amount_total,0.00)- coalesce(invoice.freight_charges,0.00) - coalesce(invoice.amazon_commission,0.00)) * agent.rate / 100,0.00)::numeric,2) as potential_commission,
            round(coalesce(agent.rate,0.00)::numeric,2) || ' %' as rate,
            NULL as payment_date,
            round(coalesce(invoice.amount_total,0.00)) as invoice_total,
            0 AS payment_amount,
            agent.amount as commission_total, 
            agent.rate as commission_percentage,
            0 AS commission_amount            
        from account_invoice_line_agent as agent 
        left join account_move as invoice on invoice.id = agent.invoice_id 
        left join account_move_line line on line.move_id = invoice.id
        left join account_account aa on line.account_id = aa.id
        left join res_partner as partner on agent.agent_id = partner.id
        left join res_partner as customer on customer.id=invoice.partner_id
        left join payments as p on p.invoice_id = invoice.id
            
        where 
            aa.account_type IN ('asset_receivable', 'liability_payable')
            AND invoice.move_type = 'out_invoice'
            AND agent.rate > 0
            AND invoice.state = 'posted'
            AND p.part_id IS NULL""" + agents + allowed_companies + f"""
        ORDER BY agent.agent_id,invoice.date)

        UNION
        
        (select 
            coalesce(agent.agent_id) AS agent_id,
            invoice.date AS invoiced_date,
            invoice.id AS invoice_id,
            customer.name as customer_name,
            invoice.partner_id AS partner_id,
            round(coalesce(invoice.amount_total - invoice.freight_charges + invoice.discount_total,0.00)::numeric,2) as gross,
            round(coalesce(invoice.discount_total,0.00)::numeric,2) as discount,
            round(coalesce(invoice.freight_charges,0.00)::numeric,2) as freight_charges,
            round(coalesce(invoice.amazon_commission,0.00)::numeric,2) as amazon_charges,
            round(coalesce(invoice.amount_total,0.00)::numeric,2) as net_sale,
            CASE 
                    WHEN invoice.move_type = 'out_refund' THEN round(coalesce(coalesce(-(invoice.amount_total),0.00) - coalesce(invoice.freight_charges,0.00) - coalesce(invoice.amazon_commission,0.00),0.00)::numeric,2) 
                    ELSE round(coalesce(coalesce(invoice.amount_total,0.00) - coalesce(invoice.freight_charges,0.00) - coalesce(invoice.amazon_commission,0.00),0.00)::numeric,2)
                END AS potential_commission_amt,
            CASE 
                    WHEN invoice.move_type = 'out_refund' THEN round(coalesce((coalesce(-(invoice.amount_total),0.00)- coalesce(invoice.freight_charges,0.00) - coalesce(invoice.amazon_commission,0.00)) * agent.rate / 100,0.00)::numeric,2) 
                    ELSE round(coalesce((coalesce(invoice.amount_total,0.00)- coalesce(invoice.freight_charges,0.00) - coalesce(invoice.amazon_commission,0.00)) * agent.rate / 100,0.00)::numeric,2)
                END AS potential_commission,
            round(coalesce(agent.rate,0.00)::numeric,2) || ' %' as rate,
            in_move.date as payment_date,
            round(coalesce(invoice.amount_total,0.00)) as invoice_total,
               CASE 
                    WHEN invoice.move_type = 'out_refund' THEN -part.amount 
                    ELSE part.amount
                END AS payment_amount,
            agent.amount as commission_total, 
            agent.rate as commission_percentage, 
            CASE 
                WHEN invoice.move_type = 'out_refund' THEN -((agent.rate * part.amount) / 100)
                ELSE (agent.rate * part.amount) / 100
            END AS commission_amount
            
        from account_invoice_line_agent as agent 
        left join account_move as invoice on invoice.id = agent.invoice_id 
        left join account_move_line line on line.move_id = invoice.id 
        left join res_partner as partner on agent.agent_id = partner.id
        left join res_partner as customer on customer.id=invoice.partner_id
        left join payments as pymnts on pymnts.invoice_id = invoice.id
        JOIN account_partial_reconcile part ON
            part.debit_move_id = line.id
            OR
            part.credit_move_id = line.id
            
        JOIN account_move_line in_move_line on 
            part.credit_move_id = in_move_line.id
        JOIN account_move in_move on 
            in_move_line.move_id = in_move.id
        JOIN account_account in_account on
            in_account.id = in_move_line.account_id
        where 
            in_account.account_type IN ('asset_receivable', 'liability_payable')
            AND invoice.move_type in ('out_invoice','out_refund')
            AND agent.rate > 0
            AND (part.max_date <= '{date_end}' AND (('{date_start}' <= pymnts.max_date OR pymnts.max_date IS NULL) OR ('{date_end}' <= pymnts.max_date OR pymnts.max_date IS NULL))) """
        query += agents
        query += allowed_companies
        query += f"""
            order by
                agent.agent_id, in_move.date, invoice.id);
                """
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        invoice_ids = []
        balance_amt = 0.0
        for com_data in result:
            if not (com_data['invoice_id'],com_data['agent_id']) in invoice_ids:
                invoice_ids.append((com_data['invoice_id'],com_data['agent_id']))
                balance_amt = 0.0
                balance_amt += com_data['commission_amount']
                balance_commission = com_data['potential_commission'] - com_data['commission_amount']
            else:
                balance_amt += com_data['commission_amount']
                balance_commission = com_data['potential_commission'] - balance_amt
            invoice_date = com_data['invoiced_date'].strftime('%Y-%m-%d')
            payment_date = False
            if com_data['payment_date']:
                payment_date = com_data['payment_date'].strftime('%Y-%m-%d')
            if payment_date:
                insert_query = f"""insert into agent_commission_reports(invoice_date,invoice_id,invoice_partner_id,gross_amount,discount_amount,freight_charges,amazon_commission,net_sale,agent_id,potential_commission_amt,potential_commission,date_paid,amount_paid,commissionable_amount,commission,balance_commission) values('{invoice_date}',{com_data['invoice_id']},{com_data['partner_id']},{com_data['gross']},{com_data['discount']},{com_data['freight_charges']},{com_data['amazon_charges']},{com_data['net_sale']},{com_data['agent_id']},{com_data['potential_commission_amt']},{com_data['potential_commission']},'{payment_date}',{com_data['payment_amount']},{com_data['payment_amount']},{com_data['commission_amount']},{balance_commission})"""
            else:
                insert_query = f"""insert into agent_commission_reports(invoice_date,invoice_id,invoice_partner_id,gross_amount,discount_amount,freight_charges,amazon_commission,net_sale,agent_id,potential_commission_amt,potential_commission,amount_paid,commissionable_amount,commission,balance_commission) values('{invoice_date}',{com_data['invoice_id']},{com_data['partner_id']},{com_data['gross']},{com_data['discount']},{com_data['freight_charges']},{com_data['amazon_charges']},{com_data['net_sale']},{com_data['agent_id']},{com_data['potential_commission_amt']},{com_data['potential_commission']},{com_data['payment_amount']},{com_data['payment_amount']},{com_data['commission_amount']},{balance_commission})"""
            self.env.cr.execute(insert_query)
        return {
            'name': 'Sales Commission Report',
            'view_mode': 'tree',
            'view_type': 'tree',
            'res_model': 'agent.commission.reports',
            'view id': self.env.ref('commission.agent_commission_reports_tree_view').id,
            'context': {'search_default_agents': 1},
            'type': 'ir.actions.act_window'
        }