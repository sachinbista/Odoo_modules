# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    transit_loc_id = fields.Many2one(
        'stock.location', string='Transit Location',
        domain="[('usage', '=', 'transit'),\
        ('company_id', '=', company_id)]")
    # debit_account_id = fields.Many2one(
    # 'account.account', string='Debit Account')
    # credit_account_id = fields.Many2one(
    # 'account.account', string='Credit Account')
    account_journal_id = fields.Many2one(
        'account.journal', string='Journal')
    account_payable_id = fields.Many2one(
        'account.account',
        string="Account Payable",
        domain="[('account_type', '=', 'liability_payable'),\
         ('deprecated', '=', False)]",
        help="This account will be used instead of the default one\
        as the payable account for the intercompany transfer")
    account_receivable_id = fields.Many2one(
        'account.account',
        string="Account Receivable",
        domain="[('account_type', '=', 'asset_receivable'),\
        ('deprecated', '=', False)]",
        help="This account will be used instead of the default\
        one as the receivable account for the intercompany transfer")
    account_income_id = fields.Many2one(
        'account.account',
        domain="[('account_type', '=', 'income'),\
        ('deprecated', '=', False)]",
        string='Income Account')
    account_expense_id = fields.Many2one(
        'account.account',
        domain="[('account_type', '=', 'expense_direct_cost'),\
        ('deprecated', '=', False)]",
        string='Expense Account')
    outgoing_route_id = fields.Many2one(
        'stock.route',
        string='Outgoing Route',
        domain="[('warehouse_selectable', '=', True),\
        ('company_id', '=', company_id)]")
    incoming_route_id = fields.Many2one(
        'stock.route',
        string='Incoming Route',
        domain="[('warehouse_selectable', '=', True),\
        ('company_id', '=', company_id)]")
    resupply_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Resupply Warehouse', check_company=False)

    @api.model
    def name_search(
            self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('all_warehouse', False):
            domain = args or []
            if self._context.get('dest_company_id', False):
                domain = expression.AND([
                    args or [],
                    [('name', operator, name),
                     ('company_id', '=', self._context['dest_company_id'])]
                ])
            elif self._context.get('company_id', False):
                domain = expression.AND([
                    args or [],
                    [('name', operator, name),
                     ('company_id', '=', self._context['company_id'])]
                ])
            return self.sudo().search(domain, limit=limit).name_get()
        return super(StockWarehouse, self).name_search(
            name, args, operator, limit)

    def update_warehouse_account(self, current_company_id):
        self = self.sudo()
        journal = self.env['ir.config_parameter'].get_param(
            'resupply.account.journal')
        receivable_id = self.env['ir.config_parameter'].get_param(
            'resupply.account.receivable')
        payable_id = self.env['ir.config_parameter'].get_param(
            'resupply.account.payable')
        income_id = self.env['ir.config_parameter'].get_param(
            'resupply.account.income')
        expense_id = self.env['ir.config_parameter'].get_param(
            'resupply.account.expense')
        warehouse_ids = self.env['stock.warehouse'].search([
            ('company_id', '=', current_company_id.id)
        ])
        for warehouse in warehouse_ids:
            vals = {}
            if not warehouse.account_journal_id:
                if journal:
                    journal_id = self.env['account.journal'].search([
                        ('code', '=', journal),
                        ('company_id', '=', current_company_id.id),
                    ], limit=1)
                    vals.update(
                        {'account_journal_id': journal_id and journal_id.id})
            if not warehouse.account_receivable_id:
                if receivable_id:
                    account_receivable_id = self.env['account.account'].search(
                        [('deprecated', '=', False),
                         ('code', '=', receivable_id),
                         ('company_id', '=', current_company_id.id)
                         ], limit=1)
                    vals.update({
                        'account_receivable_id': account_receivable_id
                        and account_receivable_id.id
                        })
            if not warehouse.account_payable_id:
                if payable_id:
                    account_payable_id = self.env['account.account'].search([
                        ('deprecated', '=', False),
                        ('code', '=', payable_id),
                        ('company_id', '=', current_company_id.id)
                    ], limit=1)
                    vals.update(
                        {'account_payable_id': account_payable_id
                         and account_payable_id.id})
            if not warehouse.account_income_id:
                if income_id:
                    account_income_id = self.env['account.account'].search([
                        ('deprecated', '=', False),
                        ('code', '=', income_id),
                        ('company_id', '=', current_company_id.id)
                    ], limit=1)
                    vals.update(
                        {'account_income_id': account_income_id
                         and account_income_id.id})
            if not warehouse.account_expense_id:
                if expense_id:
                    account_expense_id = self.env['account.account'].search([
                        ('deprecated', '=', False),
                        ('code', '=', expense_id),
                        ('company_id', '=', current_company_id.id)
                    ], limit=1)
                    vals.update(
                        {'account_expense_id': account_expense_id
                         and account_expense_id.id})
            warehouse.write(vals)
        return True

    def _get_routes_values(self):
        res = super(StockWarehouse, self)._get_routes_values()
        res.update({
            'incoming_route_id': {
                'routing_key': self.reception_steps,
                'depends': ['reception_steps'],
                'route_update_values': {
                    'name': self._format_routename(
                        route_type=self.reception_steps),
                    'active': self.active,
                },
                'route_create_values': {
                    'product_categ_selectable': True,
                    'warehouse_selectable': True,
                    'product_selectable': False,
                    'company_id': self.company_id.id,
                    'sequence': 9,
                },
                'rules_values': {
                    'active': True,
                    'propagate_cancel': True,
                },
            },
            'outgoing_route_id': {
                'routing_key': self.delivery_steps,
                'depends': ['delivery_steps'],
                'route_update_values': {
                    'name': self._format_routename(
                        route_type=self.delivery_steps),
                    'active': self.active,
                },
                'route_create_values': {
                    'product_categ_selectable': True,
                    'warehouse_selectable': True,
                    'product_selectable': False,
                    'company_id': self.company_id.id,
                    'sequence': 10,
                },
                'rules_values': {
                    'active': True,
                    'propagate_carrier': True
                }
            },
        })
        return res

    def _get_locations_values(self, vals, code=False):
        sub_locations = super(
            StockWarehouse,
            self)._get_locations_values(
            vals,
            code)
        company_id = vals.get(
            'company_id', self.default_get(
                ['company_id'])['company_id'])
        if company_id:
            company_id = self.env['res.company'].browse(company_id)
            sub_locations.update({
                'transit_loc_id': {
                    'name': company_id.name + ' Resupply - Same Company',
                    'usage': 'transit',
                    'company_id': company_id.id,
                    'is_intercompany': True,
                },
            })
        return sub_locations

    @api.model_create_multi
    def create(self, vals_list):
        warehouse_records = super(StockWarehouse, self).create(vals_list)
        for warehouse in warehouse_records:
            company_id = warehouse.company_id
            journal_id = None
            account_receivable_id = None
            account_payable_id = None
            account_income_id = None
            account_expense_id = None
            journal = self.env['ir.config_parameter'].sudo().get_param(
                'resupply.account.journal')
            receivable_id = self.env['ir.config_parameter'].sudo().get_param(
                'resupply.account.receivable')
            payable_id = self.env['ir.config_parameter'].sudo().get_param(
                'resupply.account.payable')
            income_id = self.env['ir.config_parameter'].sudo().get_param(
                'resupply.account.income')
            expense_id = self.env['ir.config_parameter'].sudo().get_param(
                'resupply.account.expense')
            if journal:
                journal_id = self.env['account.journal'].search([
                    ('code', '=', journal),
                    ('company_id', '=', company_id.id),
                ], limit=1)
            if receivable_id:
                account_receivable_id = self.env['account.account'].search([
                    ('deprecated', '=', False),
                    ('code', '=', receivable_id),
                    ('company_id', '=', company_id.id)
                ], limit=1)
            if payable_id:
                account_payable_id = self.env['account.account'].search([
                    ('deprecated', '=', False),
                    ('code', '=', payable_id),
                    ('company_id', '=', company_id.id)
                ], limit=1)
            if income_id:
                account_income_id = self.env['account.account'].search([
                    ('deprecated', '=', False),
                    ('code', '=', income_id),
                    ('company_id', '=', company_id.id)
                ], limit=1)
            if expense_id:
                account_expense_id = self.env['account.account'].search([
                    ('deprecated', '=', False),
                    ('code', '=', expense_id),
                    ('company_id', '=', company_id.id)
                ], limit=1)
            warehouse.write({
                'account_journal_id': journal_id and journal_id.id,
                'account_receivable_id': account_receivable_id and account_receivable_id.id,
                'account_payable_id': account_payable_id and account_payable_id.id,
                'account_income_id': account_income_id and account_income_id.id,
                'account_expense_id': account_expense_id and account_expense_id.id
            })
        return warehouse_records
