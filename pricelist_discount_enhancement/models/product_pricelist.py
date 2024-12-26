from odoo import fields, models,api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'product.pricelist'

    is_tax_exempt = fields.Boolean(string="Is Tax Exempt", default=False)
