from odoo import models
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def print_label(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get("active_ids") if active_model == 'stock.quant' else self.ids
        quants = self.browse(active_ids)
        if not quants:
            raise UserError("You have not selected any record. Nothing to print")

        print_counts = []
        for quant in quants:
            if quant.quantity < 0:
                continue
            print_counts.append((0, 0, {'product_id': quant.product_id.product_tmpl_id.id,
                                        'quantity': 1,
                                        'lot_id': quant.lot_id.id}))

        print_wizard = self.env['print.wizard'].create({
            'print_count_ids': print_counts,
            'model': self._name,
            'quant_ids': [(6, 0, quants.ids)]
        })
        action = self.env['ir.actions.act_window']._for_xml_id('bista_zpl_labels.print_wizard_action')
        action['res_id'] = print_wizard.id
        return action
