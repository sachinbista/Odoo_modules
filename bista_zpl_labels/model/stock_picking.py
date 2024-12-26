from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def print_label(self):
        print_counts = []
        for move in self.move_line_ids:
            print_counts.append((0, 0, {'product_id': move.product_id.product_tmpl_id.id,
                                        'quantity': move.qty_done,
                                        'move_line_id': move.id,
                                        'lot_id': move.lot_id.id}))
        print_wizard = self.env['print.wizard'].create({
            'picking_ids': [self.id],
            'print_count_ids': print_counts,
            'model': self._name
        })
        action = self.env['ir.actions.act_window']._for_xml_id('bista_zpl_labels.print_wizard_action')
        action['res_id'] = print_wizard.id
        return action


    def action_open_label_layout(self):
        return self.print_label()

