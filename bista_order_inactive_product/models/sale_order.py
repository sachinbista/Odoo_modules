from odoo import fields, models, _, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection_add=[
        ('rule_fail', 'Review'),
    ], ondelete={'rule_fail': 'cascade'})
    is_sale_rule = fields.Boolean(string="Sale Rule", copy=False)

    def action_confirm(self):
        """Check if the order has inactive product and user has permission to confirm the order"""
        if self._context.get("skip_rule"):
            self.state = 'draft'
            return super().action_confirm()
        user_is_admin = self.env.user.has_group('bista_order_inactive_product.group_sale_rule_admin')
        if self.is_sale_rule:
            if user_is_admin:
                return {
                    'name': _('Review Sale Order'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'order.review.wizard',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'views': [(False, 'form')],
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'default_name': _("Order break the sales rule.\n"
                                          "Do you want to confirm the order ?")
                    }
                }
            else:
                self.state = 'rule_fail'
                self.is_sale_rule = False
                for line in self.order_line:
                    line.check_price_rule(line, self.pricelist_id)
                inactive_product = self.order_line.filtered(lambda l: l.product_id.status == 'discontinued')
                for line in inactive_product:
                    line.order_id.message_post(body=_("Product %s is Discontinued. please fix it") % line.product_id.name)
                    line.order_id.is_sale_rule = True
                if not inactive_product and not self.is_sale_rule:
                    self.state = 'draft'
                    return super().action_confirm()
                return
        return super().action_confirm()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self,vals_list):
        """Check if the product is inactive and send a message to the user"""
        res = super().create(vals_list)
        pricelist_id = res.order_id.pricelist_id
        for line in res:
            if line.product_id.status == 'discontinued':
                line.order_id.message_post(body=_("Product %s is Discontinued. please fix it") % line.product_id.name)
                line.order_id.is_sale_rule = True
            self.check_price_rule(line, pricelist_id)
        return res

    def write(self,vals):
        """Check if the product is inactive and send a message to the user"""
        res = super().write(vals)
        pricelist_id = self.order_id.pricelist_id
        for line in self:
            if line.product_id.status == 'discontinued':
                line.order_id.message_post(body=_("Product %s is Discontinued. please fix it") % line.product_id.name)
                line.order_id.is_sale_rule = True
            self.check_price_rule(line, pricelist_id)
        return res

    def check_price_rule(self,line,pricelist_id):
        item = pricelist_id.item_ids.filtered(lambda l: l.product_tmpl_id == line.product_id.product_tmpl_id)
        if item and item.compute_price == 'fixed' and item.fixed_price != line.price_unit:
            line.order_id.is_sale_rule = True
            line.order_id.message_post(
                body=_("Product %s price not match with pricelist. please fix it") % line.product_id.name)
        if not item:
            line.order_id.is_sale_rule = True
            line.order_id.message_post(
                body=_("Product %s is not in pricelist. please fix it") % line.product_id.name)

