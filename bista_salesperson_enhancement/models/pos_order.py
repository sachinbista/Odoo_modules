# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'


    other_users = fields.Many2many(string='Additional Salesperson', comodel_name='res.users')

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        other_users = ui_order.get('other_users', []) or False
        if other_users:
            res.update({'other_users': [int(x) for x in other_users]})
        return res
