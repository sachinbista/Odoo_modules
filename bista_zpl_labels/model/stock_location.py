from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def print_label(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get("active_ids") if active_model == 'stock.location' else self.ids
        action = self.env['ir.actions.act_window']._for_xml_id('bista_zpl_labels.print_wizard_action')
        action['context'] = {'default_model': self._name, 'default_location_ids': [(6, 0, active_ids)]}
        return action
