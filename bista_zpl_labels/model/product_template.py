import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_label_layout(self):
        return self.print_label()

    def print_label(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get("active_ids") if active_model == 'product.template' else self.ids
        action = self.env['ir.actions.act_window']._for_xml_id('bista_zpl_labels.print_wizard_action')
        action['context'] = {'default_model': self._name, 'default_product_ids': [(6, 0, active_ids)]}
        return action
