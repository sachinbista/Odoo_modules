from odoo import models, api,fields,_


class AccountMove(models.Model):
    _inherit = 'account.move'

    transit_id = fields.Many2one('purchase.order', string='Purchase Order')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self,vals_list):
        fiscal_position_id = self._context.get('fiscal_position_id')
        if fiscal_position_id:
            fiscal_position_id = self.env['account.fiscal.position'].browse(fiscal_position_id)
            for vals in vals_list:
                if vals.get('account_id'):
                    account_line = fiscal_position_id.account_ids.filtered(
                        lambda x: x.account_src_id.id == vals['account_id'])
                    if account_line:
                        vals['account_id'] = account_line.account_dest_id.id
        return super().create(vals_list)
