from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import datetime


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
        # self.check_product_allocation()
        if self.is_sale_rule:
            if user_is_admin:
                self.check_product_allocation()
                allocation_rule = self._context.get("allocation_rule",False)
                if allocation_rule:
                    self.state = 'rule_fail'
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
                self.check_product_allocation()
                if not inactive_product and not self.is_sale_rule:
                    self.state = 'draft'
                    return super().action_confirm()
                return True
        return super().action_confirm()

    def check_product_allocation(self):
        """Check if the user has permission to confirm the order"""
        order_date = self.date_order.date()
        allocation_obj = self.env['product.allocation']
        for line in self.order_line.filtered(lambda l: l.product_id.detailed_type == 'product'):
            allocation = allocation_obj.search(
                [('partner_id', '=', self.partner_id.id), ('product_id', '=', line.product_id.id),
                 ('start_date', '<=', order_date), ('end_date', '>=', order_date)])
            if not allocation:
                allocation = allocation_obj.search(
                    [('customer_group_id', '=', self.partner_id.group_id.id), ('product_id', '=', line.product_id.id),
                     ('start_date', '<=', order_date), ('end_date', '>=', order_date)])

            if allocation:
                quantity = line.product_uom_qty + allocation.current_allocation_qty
                if quantity > allocation.allocated_qty:
                    self.message_post(body=
                    _("you are not allowed to confirm product %s  more quantity then product allocated quantity %s")
                    % (line.product_id.name, allocation.allocated_qty))
                    self.is_sale_rule = True
                    self.with_context(allocation_rule=True)

            product_allocation = allocation_obj.search([('product_id', '=', line.product_id.id),
                 ('start_date', '<=', order_date), ('end_date', '>=', order_date)])
            if product_allocation and not allocation:
                self.message_post(body=
                                  _("Product %s allocation not available for %s")
                                  % (line.product_id.name, self.partner_id.name))
                self.is_sale_rule = True
                self.with_context(allocation_rule=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self,vals_list):
        """Check if the product is inactive and send a message to the user"""
        res = super().create(vals_list)
        pricelist_id = res.order_id.pricelist_id
        for line in res.filtered(lambda l: l.product_id.detailed_type == 'product'):
            if line.product_id.status == 'discontinued':
                line.order_id.message_post(body=_("Product %s is Discontinued. please fix it") % line.product_id.name)
                line.order_id.is_sale_rule = True
            self.check_price_rule(line, pricelist_id)
        res.order_id.check_product_allocation()
        return res

    def write(self,vals):
        """Check if the product is inactive and send a message to the user"""
        res = super().write(vals)
        pricelist_id = self.order_id.pricelist_id
        for line in self.filtered(lambda l: l.product_id.detailed_type == 'product'):
            if line.product_id.status == 'discontinued':
                line.order_id.message_post(body=_("Product %s is Discontinued. please fix it") % line.product_id.name)
                line.order_id.is_sale_rule = True
            self.check_price_rule(line, pricelist_id)
        return res

    def check_price_rule(self,line,pricelist_id):
        """Check if the product price is not match with the pricelist and send a message to the user"""
        current_datetime = datetime.now()
        item = pricelist_id.item_ids.filtered(
            lambda rule: (
            (rule.applied_on == '1_product' and rule.product_tmpl_id == line.product_id.product_tmpl_id)
             or (rule.applied_on == '3_global')
             or (rule.applied_on == '0_product_variant' and rule.product_id == line.product_id)
             or (rule.applied_on == '2_product_category' and line.product_id.categ_id == rule.categ_id))
            and ((rule.date_start and rule.date_end and rule.date_start <= current_datetime <= rule.date_end) or
                (not rule.date_start and not rule.date_end))
            )

        # item = pricelist_id.item_ids.filtered(lambda l: l.product_tmpl_id == line.product_id.product_tmpl_id)
        if len(item) > 1:
            raise UserError(_("Multiple pricelist item found for product %s") % line.product_id.name)
        if item and item.compute_price == 'fixed' and item.fixed_price != line.price_unit:
            line.order_id.is_sale_rule = True
            line.order_id.message_post(
                body=_("Product %s price not match with pricelist. please fix it") % line.product_id.name)
        if not item:
            line.order_id.is_sale_rule = True
            line.order_id.message_post(
                body=_("Product %s is not in pricelist. please fix it") % line.product_id.name)

