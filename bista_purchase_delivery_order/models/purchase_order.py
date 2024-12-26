from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        super(PurchaseOrder, self).onchange_partner_id()
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.picking_type_id = False
        else:
            self.picking_type_id = self.partner_id.delivery_type_id

        return {}
