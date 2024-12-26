# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models


class AgentCommissionReport(models.AbstractModel):
    _name = 'royalty.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Royalty Report Handler'

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

        royalty_agent_domain = [('is_royalty_agent', '=', 'True')]
        if options.get('royalty_agent') and options.get('royalty_agents_ids'):
            royalty_agent_domain.append(('id', 'in', options.get('royalty_agents_ids')))
        royalty_agents = self.env['res.partner'].search(royalty_agent_domain)

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
              invoice.date AS invoice_date, 
              invoice.name AS invoice_name,
              rp.name as customer_name,
              jsonb_extract_path_text(pt.name, 'en_US') as product_name,
              agent.name as agent_name,
              prl.is_dropship as dropship,
              invoice.move_type as invoice_type,
              r.royalty_percentage as royalty_percentage, 
              invoice.amount_total - invoice.freight_charges + invoice.discount_total as gross,
              invoice.discount_total as discount,
              invoice.freight_charges as freight_charges,
              case when {store_sql} then invoice.amount_total * {amazon_commission_rate} / 100 else 0 end as amazon_commission,
              invoice.amount_total as net_sale,
              case when {store_sql} then invoice.amount_total - invoice.freight_charges - (invoice.amount_total * {amazon_commission_rate} / 100) else invoice.amount_total - invoice.freight_charges end as potential_royalty_amt,
              case when {store_sql} then (invoice.amount_total - invoice.freight_charges - (invoice.amount_total * {amazon_commission_rate} / 100)) * r.royalty_percentage / 100 else (invoice.amount_total - invoice.freight_charges) * r.royalty_percentage / 100 end as potential_royalty
            FROM 
              account_move invoice
              left join res_company company on company.id = invoice.company_id
              join res_partner rp on rp.id = invoice.partner_id
              join account_move_line aml on aml.move_id = invoice.id
              left join product_product pp on pp.id = aml.product_id
              left join product_royalty_list prl on prl.product_id = pp.id
              right join royalty r on r.id = prl.royalty_id
              left join product_template pt on pt.id = pp.product_tmpl_id
              left join res_partner agent on agent.id = prl.partner_id
            WHERE 
              pt.detailed_type = 'product' 
              and aml.is_dropship = prl.is_dropship
              and invoice.move_type in ('out_invoice') 
              and invoice.state in ('posted') 
              and invoice.date >= '{date_from}' 
              and invoice.date <= '{date_to}'
        """

        if royalty_agents and royalty_agents.ids:
            if len(royalty_agents.ids) > 1:
                sql += f" and agent.id in {tuple(royalty_agents.ids)} "
            else:
                sql += f" and agent.id = {royalty_agents.ids[0]} "
        else:
            sql += f" and agent.id = 0"

        if allowed_companies and allowed_companies.ids:
            if len(allowed_companies.ids) > 1:
                sql += f" and company.id in {tuple(allowed_companies.ids)} "
            else:
                sql += f" and company.id = {allowed_companies.ids[0]} "
        else:
            sql += f" and company.id = 0"

        sql += f""" 
                GROUP BY invoice.date, invoice.name, company.name, rp.name, aml.product_id, pt.name, prl.royalty_rate, 
                r.royalty_percentage,
                prl.is_dropship, invoice.move_type, agent.id, invoice.amount_total, 
                invoice.freight_charges, invoice.discount_total, invoice.goflow_store_id
                ORDER BY invoice.date, invoice.name, rp.name, agent.name, pt.name 
            """

        self._cr.execute(sql)
        result = self._cr.dictfetchall()

        agent_list = sorted(list(set([value['agent_name'] for value in result])))
        for agent in agent_list:
            agent_invoices_lines = []

            invoices_lines = list(filter(lambda line: line['agent_name'] == agent, result))
            invoice_list = sorted(list(set([value['invoice_name'] for value in invoices_lines])))
            for invoice_id in invoice_list:
                agent_invoice_lines = []
                invoice_lines = list(filter(lambda line: line['invoice_name'] == invoice_id, invoices_lines))
                for invoice in invoice_lines:
                    line_column = [
                        {'name': invoice['invoice_date'] or '', 'style': 'text-align:left;'},
                        {'name': invoice['invoice_name'] or '', 'style': 'text-align:left;'},
                        {'name': invoice['customer_name'] or '', 'style': 'text-align:left;'},
                        {'name': invoice['product_name'] or '', 'style': 'text-align:left;'},
                        {'name': invoice['agent_name'] or '', 'style': 'text-align:left;'},
                        {'name': '$ {:,.2f}'.format(invoice['gross'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['discount'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['freight_charges'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['amazon_commission'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['net_sale'] or 0.0)},
                        {'name': '$ {:,.2f}'.format(invoice['potential_royalty_amt'] or 0.0)},
                        {'name': str(invoice['royalty_percentage'] or 0.0) + ' %'},
                        {'name': '$ {:,.2f}'.format(invoice['potential_royalty'] or 0.0)},
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
