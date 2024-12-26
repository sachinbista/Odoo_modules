from odoo import models, fields, api, _
from odoo.tools import float_round


class StockQuant(models.Model):
    _inherit = "stock.quant"

    product_packaging_id = fields.Many2one('product.packaging', 'Packaging')
    packaging_qty = fields.Float(
        string="Packaging Quantity",
        compute='_compute_product_packaging_qty',
        store=True, readonly=False, precompute=True)

    @api.depends('product_packaging_id', 'product_uom_id', 'quantity')
    def _compute_product_packaging_qty(self):
        for record in self:
            if not record.product_packaging_id:
                record.packaging_qty = False
            else:
                packaging_uom_id = record.product_packaging_id.product_uom_id
                packaging_uom_qty = record.product_uom_id._compute_quantity(record.quantity, packaging_uom_id)
                record.packaging_qty = float_round(
                    packaging_uom_qty / record.product_packaging_id.qty,
                    precision_rounding=packaging_uom_id.rounding)

    @api.model_create_multi
    def create(self, vals_list):
        ctx = dict(self.env.context) or {}
        quants = self.env['stock.quant']
        for vals in vals_list:
            if 'product_packaging_id' in ctx:
                vals.update({'product_packaging_id': ctx['product_packaging_id']})
            quant = super().create(vals)
            quants |= quant
        return quants

    def write(self, vals):
        ctx = dict(self.env.context) or {}
        if 'product_packaging_id' in ctx:
            vals.update({'product_packaging_id': ctx['product_packaging_id']})
        return super(StockQuant, self).write(vals)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _action_done(self):
        ctx = dict(self.env.context) or {}
        for ml in self:
            product_packaging_id = ml.product_packaging_id or ml.move_id.product_packaging_id
            if product_packaging_id:
                ctx.update({'product_packaging_id': product_packaging_id.id})
            super(StockMoveLine, ml.with_context(ctx))._action_done()

