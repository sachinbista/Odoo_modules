from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Picking ID')
