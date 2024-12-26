from odoo import fields, models,api, _


class CountryTax(models.Model):
    _name = 'country.tax'
    _description = 'Country Tax'
    _rec_name = 'country_id'

    country_id = fields.Many2one('res.country', string="Country")
    tax_id = fields.Many2one('account.tax', string="Tax")
