# Copyright 2018-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CommissionMixin(models.AbstractModel):
    _inherit = "commission.mixin"

    def _prepare_agent_vals(self, agent, commission_id=None):
        return {"agent_id": agent.id, "commission_id": commission_id[0].id if commission_id else agent.commission_id.id}