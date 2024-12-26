# -*- encoding: utf-8 -*-


from odoo import fields,api,models,_

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    other_users = fields.Many2many(string='Additional Salesperson', comodel_name='res.users')
    user_count = fields.Integer(compute='_compute_total_user', store=True)

    @api.depends('other_users', 'user_id')
    def _compute_total_user(self):
        for rec in self:
            rec.user_count = len(rec.other_users.filtered(lambda x: x.active == True)) + len(
            rec.user_id.filtered(lambda x: x.active == True))

