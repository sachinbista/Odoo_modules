from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     res = super(AccountMoveLine, self).create(vals_list)
    #     # print("vals_listttttttt",vals_list)
    #     if vals_list:
    #         move_id = vals_list[0].get('move_id')
    #         analytic = self.env['account.move.line'].search([('move_id','=',move_id)])
    #         for line in analytic:
    #             analytic_distribution = line.analytic_distribution
    #             invoice_lines = self.env['account.move.line'].search([
    #                 ('move_id', '=', move_id),
    #                 ('analytic_distribution', '=', False)
    #             ])
    #             # print("firstinnnnnnnnn",invoice_lines)
    #             for line in invoice_lines:
    #                 line.write({
    #                     'analytic_distribution': analytic_distribution
    #                 })
    #
    #     return res

