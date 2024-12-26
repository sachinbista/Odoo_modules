from odoo import _, fields, models,_


class StockMove(models.Model):
    _inherit='stock.move'

    parent_id=fields.Many2one('res.partner',related='partner_id.parent_id')
#
#
#     def backorder_stock_report(self):
#         partner_customer_xml_id = self.env.ref('stock.stock_location_customers')
#         domain = [('location_dest_id', '=',partner_customer_xml_id.id)]
#         # return {
#         #     'name': _("Stock Move Backorder"),
#         #     'res_model': 'stock.move',
#         #     'type': 'ir.actions.act_window',
#         #     'view_id': self.env.ref('stock.view_move_tree').id,
#         #     # 'context': "{'type':'out_invoice'}",
#         #     'view_type': 'tree',
#         #     'view_mode': 'tree',
#         #     'domain': domain,
#         #     'target': 'new'
#         # }
#
#
#         return {
#             'name': _('test'),
#             'view_type': 'tree',
#              'view_mode': 'tree,form',
#             'view_id': self.env.ref('stock.view_move_tree').ids,
#             'res_model': 'stock.move',
#             # 'context': "{'type':'out_invoice'}",
#             'type': 'ir.actions.act_window',
#             'views': [[False, 'tree']],
#             'target': 'new',
#             # 'domain': domain,
#         }
