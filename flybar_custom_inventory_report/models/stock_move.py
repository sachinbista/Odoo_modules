from odoo import api, fields, models, _

class StockMove(models.Model):
    _inherit = 'stock.move'

    def get_expected_cases(self):
        expected_cases = 0.0
        if self.purchase_line_id:
            if self.product_id and self.purchase_line_id.product_packaging_id.qty > 0.0:
                expected_cases = self.purchase_line_id.product_qty / self.purchase_line_id.product_packaging_id.qty
        else:
            if self.product_id and self.product_packaging_id.qty > 0.0:
                expected_cases = self.product_uom_qty / self.product_packaging_id.qty

        return round(expected_cases, 2)

    def get_variance(self):
        variance = 0.0
        if self.purchase_line_id:
            variance = self.purchase_line_id.product_qty - self.purchase_line_id.qty_received
        else:
            variance = self.product_uom_qty - self.quantity_done
        return round(variance, 2)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def get_expected_cases(self):
        expected_cases = qty = 0.0
        if self.qty_done > 0.0:
            qty = self.qty_done
        else:
            qty = self.reserved_uom_qty
        if self.product_id and self.product_packaging_id.qty > 0.0:
            expected_cases = qty / self.product_packaging_id.qty
        return expected_cases

class Stockquant(models.Model):
    _inherit = 'stock.quant.package'

    product_length = fields.Float("length")
    product_width = fields.Float("width")
    product_height = fields.Float("height")

    def get_picking_id(self):
        print("context-Test======================>", self.env.context)
        # move_line = self.env['stock.move.line'].search([('package_id', '=', self.id),('picking_id', '!=', False)], limit=1)
        # if not move_line:
        move_line = self.env['stock.move.line'].search([('result_package_id', '=', self.id),('picking_id', '!=', False)], limit=1)
        return move_line.picking_id

    def get_move_line_ids(self):
        move_line_ids = self.env['stock.move.line'].search([('picking_id', '!=', False),('package_id', '=', self.id),('result_package_id', '=', self.id)],limit=1)
        return move_line_ids

class Stockquant(models.Model):
    _inherit = 'stock.quant'

    def get_move_line_package(self):
        # product_packaging_id = self.env['stock.move.line'].search([('package_id', '=', self.package_id.id),('product_packaging_id', '!=', False),('picking_id', '!=', False)],limit=1).product_packaging_id
        # if not product_packaging_id:
        product_packaging_id = self.env['stock.move.line'].search( [('result_package_id', '=', self.package_id.id), ('product_packaging_id', '!=', False),('picking_id', '!=', False)],limit=1).product_packaging_id
        return product_packaging_id
