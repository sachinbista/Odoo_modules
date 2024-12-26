from odoo import models,fields,exceptions,api,_
from odoo.exceptions import AccessError, UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'uom.uom'

    sequence_id = fields.Many2one('ir.sequence',string="Sequence")