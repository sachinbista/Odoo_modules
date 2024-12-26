from odoo import models
import re


class LotSerial(models.Model):
    _inherit = "stock.lot"

    def print_label(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get("active_ids") if active_model == 'stock.lot' else self.ids
        action = self.env['ir.actions.act_window']._for_xml_id('bista_zpl_labels.print_wizard_action')
        action['context'] = {'default_model': self._name, 'default_lot_ids': [(6, 0, active_ids)]}
        return action
