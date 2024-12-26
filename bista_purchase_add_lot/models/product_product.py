from odoo import fields, models, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('add_lot'):
            picking = self.env['stock.picking'].browse(self._context.get('add_lot'))
            product_ids = picking.move_ids_without_package.mapped('product_id').ids or []
            args = [['id', 'in', product_ids]]
        return super(ProductProduct, self).name_search(name, args=args, operator=operator, limit=limit)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """override this method to pass product ids from current picking moves"""
        if self._context.get('add_lot'):
            picking = self.env['stock.picking'].browse(self._context.get('add_lot'))
            product_ids = picking.move_ids_without_package.mapped('product_id').ids or []
            domain += [('id', 'in', product_ids)]
        return super(ProductProduct, self).search_read(domain, fields, offset, limit, order)
