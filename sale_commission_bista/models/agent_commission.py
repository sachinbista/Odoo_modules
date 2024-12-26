# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, _


class AgentCommission(models.Model):
    _name = "agent.commission"
    _description = "Agent Commission"
    _rec_name = "agent_id"

    agent_id = fields.Many2one("res.partner", string="Agent")
    commission_id = fields.Many2one("commission", string="Commission")

    agent_partner_id = fields.Many2one("res.partner")
    product_id = fields.Many2one("product.product")

    def write(self, values):
        if 'agent_id' in values or 'commission_id' in values:
            self._update_agent_line(values)
        return super().write(values)

    def _update_agent_line(self, values):
        partners = self.mapped('agent_partner_id')
        for partner in partners:
            agent_lines = self.filtered(lambda x: x.agent_partner_id == partner)
            value_agent = value_commission = False
            msg = "<b>" + _("Agent commission line updated.") + "</b><ul>"
            if 'agent_id' in values:
                value_agent = self.env['res.partner'].browse([values['agent_id']])
            if 'commission_id' in values:
                value_commission = self.env['commission'].browse([values['commission_id']])
            for agent_line in agent_lines:
                msg += "<li> Agent Line: <br/>"
                msg += _("Agent: %(old_agent)s -> %(new_agent)s",
                         old_agent=agent_line.agent_id.display_name,
                         new_agent=value_agent.display_name if value_agent else agent_line.agent_id.display_name
                         ) + "<br/>"
                msg += _("Commission: %(old_commission)s -> %(new_commission)s",
                         old_commission=agent_lines.commission_id.fix_qty,
                         new_commission=value_commission.fix_qty if value_commission else agent_line.commission_id.fix_qty
                         ) + "<br/>"
            msg += "</ul>"
            partner.message_post(body=msg)


class CommissionMixin(models.AbstractModel):
    _inherit = "commission.mixin"

    def _prepare_agents_vals_partner(self, record, settlement_type=None):
        """Utility method for getting agents creation dictionary of a partner."""
        agent_ids = []
        for agent_commission in record.agent_new_ids:
            if agent_commission.agent_id.id not in agent_ids:
                agent_ids.append(agent_commission.agent_id.id)

        # for agent_commission in line.product_id.royalty_partner_ids:
        #     if agent_commission.agent_id.id not in agent_ids:
        #         agent_ids.append(agent_commission.agent_id.id)

        agents = self.env['res.partner'].browse(agent_ids)
        if settlement_type:
            agents = agents.filtered(
                lambda x: not x.commission_id.settlement_type
                          or x.commission_id.settlement_type == settlement_type
            )
        return [(0, 0, self._prepare_agent_vals(agent, self.get_commission_id(agent, record))) for agent in agents]

    def get_commission_id(self, agent, partner):
        commission_id = partner.agent_new_ids.filtered(lambda x: x.agent_id.id == agent.id).commission_id
        if not commission_id:
            return agent.commission_id
        else:
            return commission_id
