# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    margin = fields.Monetary("Margin", compute='_compute_margin', store=True)
    margin_percent = fields.Float("Margin (%)", compute='_compute_margin', store=True, group_operator="avg")

    @api.depends('invoice_line_ids.margin', 'amount_untaxed')
    def _compute_margin(self):
        if not all(self._ids):
            for order in self:
                order.margin = sum(order.invoice_line_ids.mapped('margin'))
                order.margin_percent = order.amount_untaxed and order.margin / order.amount_untaxed

        else:
            # On batch records recomputation (e.g. at install), compute the margins
            # with a single read_group query for better performance.
            # This isn't done in an onchange environment because (part of) the data
            # may not be stored in database (new records or unsaved modifications).
            grouped_order_lines_data = self.env['account.move.line'].read_group(
                [
                    ('move_id', 'in', self.ids),
                ], ['margin', 'move_id'], ['move_id'])
            mapped_data = {m['move_id'][0]: m['margin'] for m in grouped_order_lines_data}
            for order in self:
                # order.margin = mapped_data.get(order.id, 0.0)
                # order.margin_percent = order.amount_untaxed and order.margin / order.amount_untaxed
                order.margin = sum(order.invoice_line_ids.mapped('margin'))
                order.margin_percent = order.amount_untaxed and order.margin / order.amount_untaxed


