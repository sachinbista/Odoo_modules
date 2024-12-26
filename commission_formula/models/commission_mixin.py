# © 2016 Nicola Malcontenti - Agile Business Group
# © 2016 Davide Corio - Abstract
# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html

from odoo.tools.safe_eval import safe_eval

from odoo import api, models


class CommissionLineMixin(models.AbstractModel):
    _inherit = "commission.line.mixin"

    @api.model
    def _get_formula_input_dict(self):
        return {
            "line": self.object_id,
            "self": self,
        }

    def _get_commission_amount(self, commission, subtotal):
        """Get the commission amount for the data given. To be called by
        compute methods of children models.
        """
        self.ensure_one()
        if commission and commission.commission_type == "formula":
            formula = commission.formula
            results = self._get_formula_input_dict()
            safe_eval(formula, results, mode="exec", nocopy=True)
            return float(results["result"])
        return super()._get_commission_amount(commission, subtotal)
