from odoo import fields, models, api, _
from datetime import datetime


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_pricelist_item_id',
        store=True,
        string="Pricelist Rule",
        help="Pricelist rule applied to this line"
    )

    @api.depends('product_id', 'quantity', 'move_id.pricelist_id')
    def _compute_pricelist_item_id(self):
        for line in self:
            line.pricelist_item_id = False
            if line.product_id and line.move_id.pricelist_id and line.move_id.move_type  in ['out_invoice', 'out_refund']:
                current_datetime = datetime.now()
                item = line.move_id.pricelist_id.item_ids.filtered(
                    lambda rule: (
                    (rule.applied_on == '1_product' and rule.product_tmpl_id == line.product_id.product_tmpl_id)
                    or (rule.applied_on == '3_global')
                    or (rule.applied_on == '0_product_variant' and rule.product_id == line.product_id)
                    or (rule.applied_on == '2_product_category' and  line.product_id.categ_id == rule.categ_id))
                         and ((rule.date_start and rule.date_end and rule.date_start <= current_datetime <= rule.date_end) or
                                 (not rule.date_start and not rule.date_end)                         )

                        and line.quantity >= rule.min_quantity )
                if item:
                    line.pricelist_item_id = item[0]

    @api.onchange('product_id', 'quantity', 'move_id.pricelist_id')
    def _onchange_apply_pricelist(self):
        for line in self:
            if line.pricelist_item_id:
                price = line.pricelist_item_id._compute_price(
                    product=line.product_id,
                    quantity=line.quantity,
                    uom=line.product_uom_id,
                    date=line.move_id.invoice_date,
                    currency=line.move_id.currency_id,
                )
                line.price_unit = price

                if line.pricelist_item_id.percent_price:
                    line.discount = line.pricelist_item_id.percent_price

                elif line.pricelist_item_id.fixed_price:
                    line.price_unit = line.pricelist_item_id.fixed_price
                elif ((line.pricelist_item_id.price_discount) or (line.pricelist_item_id.price_surcharge)
                    or (line.pricelist_item_id.price_round) or (line.pricelist_item_id.price_min_margin)):
                    discount = line.pricelist_item_id.price_discount or 0.0
                    surcharge = line.pricelist_item_id.price_surcharge or 0.0
                    line.discount = discount - surcharge

            else:
                line.discount = 0.0
