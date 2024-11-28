from odoo import models, api,fields,_

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('product_id','product_uom_id','move_id.partner_id')
    def _compute_tax_ids(self):
        res = super()._compute_tax_ids()
        discount = self.move_id.partner_id.discount
        for line in self:
            line.discount = discount
        return res

    is_delivery = fields.Boolean(string="Is a Delivery", default=False)

    @api.model_create_multi
    def create(self,vals_list):
        res = super().create(vals_list)
        is_require_shipping = res.move_id.partner_id.is_require_shipping
        if is_require_shipping:
            for line in res.filtered(lambda l: l.product_id.type == 'service'):
                line.is_delivery = True
        return res
