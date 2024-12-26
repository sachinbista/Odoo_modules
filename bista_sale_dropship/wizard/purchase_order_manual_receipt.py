# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID, Command


class PurchaseOrderManualReceipt(models.TransientModel):
    _inherit = 'purchase.order.manual.receipt.wizard'

    def _create_picking(self):
        res = super(PurchaseOrderManualReceipt, self)._create_picking()
        if res:
            purchase_order = self.purchase_order_id
            if purchase_order.type_of_purchase == 'dropship':
                dropship_picking = [res.id]
                if purchase_order.sudo().sh_sale_order_id.picking_ids:
                    for rec in purchase_order.sudo().sh_sale_order_id.picking_ids.filtered(lambda a: a.is_dropship):
                        if rec.id not in dropship_picking:
                            dropship_picking.append(rec.id)
                    for each_rec in purchase_order.sudo().sh_sale_order_id.picking_ids.filtered(lambda a: not a.is_dropship):
                        if each_rec.state in ('done', 'cancel'):
                            dropship_picking.append(each_rec.id)
                        elif each_rec.state != 'done':
                            total_lines_to_delete = []
                            sml_product = [each_prod.product_id for each_prod in res.move_ids_without_package]
                            lines_to_delete = each_rec.move_ids_without_package.filtered(
                                lambda rec: rec.product_id in sml_product)
                            total_lines_to_delete += lines_to_delete
                            for each_line in total_lines_to_delete:
                                each_line.sudo().write({'state': 'draft'})
                                each_line.sudo().unlink()
                            if each_rec.move_ids_without_package:
                                dropship_picking.append(each_rec.id)
                            elif each_rec and not each_rec.move_ids_without_package:
                                each_rec.sudo().unlink()
                purchase_order.sh_sale_order_id.sudo().with_company(purchase_order.sh_sale_order_id.company_id).write(
                    {'picking_ids': [(6, 0, dropship_picking)]})
            # self.purchase_order_id.sh_sale_order_id.write({'picking_ids': [Command.link(res.id)]})
        return res

