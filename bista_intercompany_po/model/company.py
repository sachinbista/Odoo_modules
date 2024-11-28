from docutils.nodes import warning

from odoo import models, api,fields,_
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'res.company'

    first_company_id = fields.Many2one('res.company', string='first Company Name')
    secound_company_id = fields.Many2one('res.company', string='Second Company Names')
    is_inter_company = fields.Boolean('Inter Company')
