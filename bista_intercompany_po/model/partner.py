from odoo import models, api,fields,_
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'res.partner'

    default_partner = fields.Boolean('Inter-company Vendor',copy=False)
    gl_account_id = fields.Many2one('account.account', string='Expense Account',copy=False)