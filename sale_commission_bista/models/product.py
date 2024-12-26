# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    royalty_partner_ids = fields.One2many('agent.commission', 'product_id')

    @api.constrains('royalty_partner_ids')
    def _check_exist_agent_id(self):
        for product in self:
            exist_product_list = []
            for commission in product.royalty_partner_ids:
                if commission.agent_id.id in exist_product_list:
                    raise ValidationError(_('Royalty Partner Agent should be one per line.'))
                exist_product_list.append(commission.agent_id.id)