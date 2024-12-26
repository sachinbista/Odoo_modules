from odoo import fields, models, api


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('current_company_id'):
            args = [('code', '=', 'incoming'),
                    ('warehouse_id.company_id', '=', self._context.get('current_company_id'))]
        return super(PickingType, self).name_search(name, args=args, operator=operator, limit=limit)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """override this method to get the picking_type based on company_id"""
        if self._context.get('current_company_id'):
            domain = [('code', '=', 'incoming'),
                      ('warehouse_id.company_id', '=', self._context.get('current_company_id'))]
        return super(PickingType, self).search_read(domain, fields, offset, limit, order)
