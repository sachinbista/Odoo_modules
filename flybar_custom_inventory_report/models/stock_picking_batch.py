from odoo import api, fields, models, _

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"
    _name = 'stock.picking.batch'
    _inherit = ['stock.picking.batch', 'printnode.mixin', 'printnode.scenario.mixin']

    def get_purchase_orders(self):
        # po = [x.picking_id.purchase_id.name for x in self.move_line_ids.filtered(lambda s: s.picking_id.purchase_id.name)]
        purchase_orders_lst = list(set([x.picking_id.purchase_id.name for x in self.move_line_ids]))
        purchase_orders_str = ', '.join(map(str, purchase_orders_lst))
        return purchase_orders_str

    def begin_receipt(self):
        # report_action = self.env.ref('flybar_custom_inventory_report.action_pre_receiver_template_report').report_action(self)
        report_action = self.print_scenarios(
            action='flybar_custom_inventory_report.print_pree_receipt_on_batch_transfer_scenario_custom')
        return report_action
