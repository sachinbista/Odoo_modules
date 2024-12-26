from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    move_id = fields.Many2one('account.move',string="Move")

    @api.model_create_multi
    def create(self,vals_list):
        for vals in vals_list:
            move = self._context.get('move_id')
            if move:
                move_id = self.env['account.move'].browse(move)
                if move_id.move_type == 'out_invoice':
                    vals.update({'picking_type_id': move_id.company_id.out_picking_type.id,
                                 'internal_order_ref':move_id.internal_order_ref,
                                 'location_id': move_id.company_id.out_picking_type.default_location_src_id.id,
                                 })
                elif move_id.move_type == 'out_refund':
                    vals.update({'picking_type_id': move_id.company_id.return_pickng_type.id,
                                 'location_id': move_id.company_id.return_pickng_type.default_location_src_id.id,
                                 'location_dest_id': move_id.company_id.return_pickng_type.default_location_dest_id.id,
                                 'internal_order_ref':move_id.internal_order_ref
                                 })
                if move_id.shopify_order_id and move_id.move_type in ['out_invoice','out_refund']:
                    vals.update({
                        'shopify_order_id': self.shopify_order_id,
                        'shopify_config_id': self.shopify_config_id.id,
                        'shopify_transaction_id': self.shopify_transaction_id,
                        'fulfillment_status': self.fulfillment_status,
                        'shopify_order_number': self.shopify_order_number,
                    })
                vals.update({'move_id': move})
        return super().create(vals_list)


class StockMove(models.Model):
    _inherit = "stock.move"

    # internal_order_ref = fields.Char(string="Order Reference/Owner's reference")

    @api.model_create_multi
    def create(self,vals_list):
        for vals in vals_list:
            move = self._context.get('move_id')
            if move:
                move_id = self.env['account.move'].browse(move)
                if move_id.move_type == 'out_invoice':
                    vals.update({
                        'picking_type_id': move_id.company_id.out_picking_type.id,
                        'location_id': move_id.company_id.out_picking_type.default_location_src_id.id
                    })
                elif move_id.move_type == 'out_refund':
                    vals.update({'picking_type_id': move_id.company_id.return_pickng_type.id,
                                 'location_id': move_id.company_id.return_pickng_type.default_location_src_id.id,
                                 'location_dest_id': move_id.company_id.return_pickng_type.default_location_dest_id.id,
                                 })
        return super().create(vals_list)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model_create_multi
    def create(self,vals_list):
        for vals in vals_list:
            move = self._context.get('move_id')
            if move:
                move_id = self.env['account.move'].browse(move)
                if move_id.move_type == 'out_invoice':
                    vals.update({'picking_type_id': move_id.company_id.out_picking_type.id,
                                 'location_id': move_id.company_id.out_picking_type.default_location_src_id.id,
                                 })
                elif move_id.move_type == 'out_refund':
                    vals.update({'picking_type_id': move_id.company_id.return_pickng_type.id,
                                 'location_id': move_id.company_id.return_pickng_type.default_location_src_id.id,
                                 'location_dest_id': move_id.company_id.return_pickng_type.default_location_dest_id.id,
                                 })
        return super().create(vals_list)

