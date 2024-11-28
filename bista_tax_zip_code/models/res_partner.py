# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tax_exemption = fields.Boolean(string="Tax Exemption")
    tax_to_exempted_ids = fields.Many2many('account.tax',  domain=[('type_tax_use', '=', 'sale')])

    @api.onchange('tax_exemption')
    def onchange_tax_exemption(self):
        for rec in self:
            if rec.tax_exemption:
                taxes_to_be_exempted = self.env['account.tax'].search([('is_for_exemption', '=', True), ('company_id', '=', self.env.company.id)])
                rec.tax_to_exempted_ids = taxes_to_be_exempted
            else:
                self.tax_to_exempted_ids = [(5, 0, 0)]