import ast
from odoo import models, fields, api, _

class QualityCheckWizard(models.TransientModel):
    _inherit = 'quality.check.wizard'

    dimension_status = fields.Boolean("Dimension Status", compute='_compute_dimension_status')

    @api.depends('current_check_id', 'check_ids')
    def _compute_dimension_status(self):
        for wiz in self:
            wiz.dimension_status = self.current_check_id.dimension_status

    def action_get_dimensions(self):
        if not self.dimension_status:
            self.current_check_id.action_get_dimensions()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.action_quality_check_wizard")
        action['context'] = dict(ast.literal_eval(action['context']))
        action['context'].update(
            self.env.context,
            default_current_check_id=self.current_check_id.id,
        )
        return action
