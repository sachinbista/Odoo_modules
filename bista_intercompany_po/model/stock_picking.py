from odoo import models, api, fields, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    internal_order_ref = fields.Char(string="Order Reference/Owner's reference")


    def button_validate(self):
        inter_company = self.env['res.company'].search([('is_inter_company', '=', True)], limit=1)
        if self.company_id == inter_company.first_company_id:
            second_company_pickings = self.env['stock.picking'].sudo().search([
                ('company_id', '=', inter_company.secound_company_id.id),
                ('origin', '=', self.origin),
                ('state', '!=', 'done')
            ])

            if second_company_pickings:
                raise UserError(
                    _("You must validate all related pickings for the  (%s) before receiving products in the  company (%s).")
                    % (inter_company.secound_company_id.name, self.company_id.name)
                )

        elif self.company_id == inter_company:
            first_company_pickings = self.env['stock.picking'].sudo().search([
                ('company_id', '=', inter_company.first_company_id.id),
                ('origin', '=', self.origin),
                ('state', '!=', 'done')
            ])

            if first_company_pickings:
                raise UserError(
                    _("You must validate all related pickings for the  (%s) before receiving products in  (%s).")
                    % (inter_company.first_company_id.name, self.company_id.name)
                )
        return super(StockPicking, self).button_validate()

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        # Inherit with correct method signature for Odoo 17
        move_vals = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)

        # Add custom reference from picking to journal entry
        if self.picking_id and self.picking_id.internal_order_ref:
            move_vals['internal_order_ref'] = self.picking_id.internal_order_ref
        return move_vals



