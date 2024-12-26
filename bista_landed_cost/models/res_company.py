from odoo import models, api,fields,_


class PurchaseOrder(models.Model):
    _inherit = 'res.company'

    in_transit_account_id = fields.Many2one('account.account',company_dependent=True, string='In Transit Account')
    is_transit = fields.Boolean('Is Transit', company_dependent=False)
