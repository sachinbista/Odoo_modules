# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError

from odoo import api, fields, models, _


class Partner(models.Model):
    _inherit = "res.partner"

    agent_new_ids = fields.One2many('agent.commission', 'agent_partner_id', string="Agents")

    is_commission_customer = fields.Boolean("Commission Customer", compute="_compute_commission_customer", store=True)

    @api.constrains('agent_new_ids')
    def _check_exist_agent_id(self):
        for partner in self:
            exist_product_list = []
            for commission in partner.agent_new_ids:
                if commission.agent_id.id in exist_product_list:
                    raise ValidationError(_('Royalty Partner Agent should be one per line.'))
                exist_product_list.append(commission.agent_id.id)

    @api.depends('agent_new_ids')
    def _compute_commission_customer(self):
        for partner in self:
            commission_customer = False
            if partner.agent_new_ids and len(partner.agent_new_ids) > 0:
                commission_customer = True
            partner.is_commission_customer = commission_customer
