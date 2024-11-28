# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime


class StateTax(models.Model):
    _name = 'state.tax'
    _description = 'State Tax'
    _rec_name = 'zip_coe'

    def _get_start_date(self):
        return datetime.now().date().replace(month=1, day=1)

    def _get_end_date(self):
        return datetime.now().date().replace(month=12, day=31)

    active = fields.Boolean(string="Active", default=True)
    state_code = fields.Char(string="State Code", required=True)
    zip_coe = fields.Char(string="Zip Code", required=True)
    tax_name = fields.Char(string="Tax Region Name", required=True)
    estimated_combined_rate = fields.Float(
        string="Estimated Combined Rate", required=True, digits=(12, 5))
    state_rate = fields.Float(string="State Rate", digits=(12, 5))
    estimated_county_rate = fields.Float(string="Estimated County Rate", digits=(12, 5))
    estimated_city_rate = fields.Float(string="Estimated City Rate", digits=(12, 5))
    estimated_special_rate = fields.Float(string="Estimated Special Rate", digits=(12, 5))
    risk_level = fields.Integer(string="Risk Level")
    start_date = fields.Date(string="Start Date", default=_get_start_date)
    end_date = fields.Date(string="End Date", default=_get_end_date)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            AccountTax = self.env['account.tax']
            if vals.get('estimated_combined_rate'):
                estimated_county_rate = vals.get('estimated_combined_rate') * float(100)
                tax_id = AccountTax.search([('type_tax_use', '=', 'sale'), ('amount', '=', estimated_county_rate)])
                tax_final_account = self.env.company.set_tax_account_zip_id and self.env.company.set_tax_account_zip_id.id or False
                if not tax_id:
                    AccountTax.create({
                        'name': str("{:.2f}".format(estimated_county_rate)) + '%',
                        'amount': estimated_county_rate,
                        'type_tax_use': 'sale',
                        'invoice_repartition_line_ids': [
                            (0, 0, {
                                'repartition_type': 'base',
                                # 'tag_ids': [(6, 0, tax_tags['invoice']['base'].ids)],
                            }),
                            (0, 0, {
                                'repartition_type': 'tax',
                                'account_id': tax_final_account,
                                # 'tag_ids': [(6, 0, tax_tags['invoice']['tax'].ids)],
                            }),
                        ],
                        'refund_repartition_line_ids': [
                            (0, 0, {
                                'repartition_type': 'base',
                                # 'tag_ids': [(6, 0, tax_tags['refund']['base'].ids)],
                            }),
                            (0, 0, {
                                'repartition_type': 'tax',
                                'account_id': tax_final_account,
                                # 'tag_ids': [(6, 0, tax_tags['refund']['tax'].ids)],
                            }),
                        ]
                    })
        return super().create(vals_list)
