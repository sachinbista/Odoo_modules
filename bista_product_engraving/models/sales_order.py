from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    engrave_line_id = fields.Many2one('sale.order.line', string='Engrave Line')
    is_engrave_line = fields.Boolean(string='Is Engrave Line?')
    engrave_html = fields.Html(string='Engrave HTML')

    def unlink(self):
        for record in self:
            if record.engrave_line_id:
                record.engrave_line_id.unlink()
        return super(SaleOrderLine, self).unlink()

    def get_description_following_lines(self):
        result = super().get_description_following_lines()
        if self.is_engrave_line:
            for res in result:
                # TODO: need to find a better way to remove 'Font:' from result list
                if res.startswith('Font:'):
                    result.remove(res)
                    break
        return result


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = super()._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        order_line = self.env['sale.order.line'].browse(values['line_id'])
        if 'engrave_msg' in kwargs and len(kwargs['engrave_msg']) > 0:
            if not order_line.is_engrave_line and not order_line.engrave_line_id:
                product_id = order_line.product_id
                engrave_text = kwargs['engrave_msg'].strip()
                # create a new sale order line for engraving
                engrave_line_data = {
                    'order_id': order_line.order_id.id,
                    'product_id': self.env.ref('bista_product_engraving.engrave_service_product').id,
                    'product_uom_qty': 1,
                    'price_unit': product_id.calculate_engrave_charges(engrave_text),
                    'is_engrave_line': True,
                }
                engrave_line_name = f"Engraving for {order_line.product_id.name}"
                engrave_line_name += f" \nText: {engrave_text}"
                engrave_line_name += f" \nFont: {kwargs['engrave_font']}"
                engrave_line_data['name'] = engrave_line_name
                engrave_line_id = self.env['sale.order.line'].create(engrave_line_data)
                order_line.write({'engrave_line_id': engrave_line_id.id})
        return values