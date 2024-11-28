from odoo import models,fields,exceptions,api,_
from odoo.exceptions import AccessError, UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    uom_id = fields.Many2one('uom.uom',string="Unit of Measure")

    @api.model_create_multi
    def create(self, vals_list):

        if vals_list[0]['uom_id']:
            uom_id = self.env['uom.uom'].browse(vals_list[0]['uom_id'])
            if uom_id.sequence_id:
                for vals in vals_list:
                    if 'company_id' in vals:
                        self = self.with_company(vals['company_id'])
                    if vals.get('name', _("New")) == _("New"):
                        seq_date = fields.Datetime.context_timestamp(
                            self, fields.Datetime.to_datetime(vals['date_order'])
                        ) if 'date_order' in vals else None
                        vals['name'] = self.env['ir.sequence'].next_by_code(
                            uom_id.sequence_id.code, sequence_date=seq_date) or _("New")
        else:
            for vals in vals_list:
                if 'company_id' in vals:
                    self = self.with_company(vals['company_id'])
                if vals.get('name', _("New")) == _("New"):
                    seq_date = fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals['date_order'])
                    ) if 'date_order' in vals else None
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'sale.order', sequence_date=seq_date) or _("New")

        return super().create(vals_list)

class SaleOrder(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def get_default_uom(self):
        if self.order_id.uom_id:
            self.product_uom = self.order_id.uom_id
