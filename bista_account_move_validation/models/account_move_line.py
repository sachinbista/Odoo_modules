# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        for x in self:
            partner = vals.get("partner_id")
            move = x.move_id
            parent_id = move.partner_id.parent_id.id if move.partner_id and move.partner_id.parent_id else False
            if move \
                    and move.partner_id \
                    and move.move_type != 'entry' \
                    and partner \
                    and partner not in [move.partner_id.id, parent_id]:
                raise UserError(
                    f"Partner on Account Move Line should be same as Account Move. "
                    f"\nAccount Move: {move.partner_id.id}"
                    f"\nAccount Move Line: {partner}")
        return super(AccountMoveLine, self).write(vals)
