# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = 'res.company'

    intercom_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        'Intercompany Analytic Account')
    inter_company_user_ids = fields.Many2many(
        'res.users',
        string='Inter Company Users')
    company_code = fields.Char("Company Code")

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('all_company', False):
            user_id = self.env.user
            company_ids = user_id.sudo().company_ids.ids or []
            domain = expression.AND([
                args or [],
                [('name', operator, name), ('id', 'in', company_ids)]
            ])
            return self.sudo().search(domain, limit=limit).name_get()
        return super(ResCompany, self).name_search(name, args, operator, limit)

    @api.model_create_multi
    def create(self, vals_list):
        company_records = super(ResCompany, self).create(vals_list)
        for res in company_records:
            company_name = ''.join(list(map(
                lambda x: x[0], res.name.split()))).upper()
            inventory_loc_id = self.env['stock.location'].sudo().search([
                ('name', 'ilike', 'Inventory adjustment'),
                ('usage', '=', 'inventory'),
                ('company_id', '=', res.id),
            ], limit=1)
            if inventory_loc_id and company_name:
                inventory_loc_id.write(
                    {'name': inventory_loc_id.name + ' ' + company_name})
        return company_records


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inter_company_user_ids = fields.Many2many(
        'res.users',
        related='company_id.inter_company_user_ids',
        string='Inter Company Users',
        readonly=False)
