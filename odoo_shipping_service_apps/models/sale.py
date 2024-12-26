# -*- coding: utf-8 -*-
#################################################################################
##    Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from collections import  Counter
from datetime import datetime, timedelta
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError##Warning
import logging
_logger = logging.getLogger(__name__)

Delivery = [
    ('none','None'),
    ('fixed','Fixed'),
    ('base_on_rule','Base on Rule'),
]

class ProductTemplate(models.Model):
    _inherit = "product.template"
    wk_packaging_ids = fields.Many2many(
        'product.packaging',
        'product_tmp_product_packaging_rel',
        'product_tmpl_id',
        'packaging_id',
        string='Packaging'
    )

class SaleOrder(models.Model):
    _inherit = "sale.order"
    carrier_price = fields.Float(
        string='Actual Carrier Charges',
        help="Actual Carrier Charges recive from api "
    )
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    
    create_package = fields.Selection(
        string='Create Package',
        selection=[('auto','Automatic'),('manual','Manual')],
        default='auto',
        help='Create  automatic package as per packing max weight limit and  max qty  ',
    )
    wk_packaging_ids = fields.One2many(
        comodel_name='product.package',
        inverse_name='order_id',
        string='Package'
    )

    quant_package_ids = fields.Many2many(
        comodel_name='stock.quant.package',
        string='Packages'
    )

    wk_shipping_weight = fields.Float("Shipping Weight", compute="_compute_shipping_weight", store=True)
   
    @api.depends('order_line', 'order_line.product_uom_qty', 'order_line.product_uom', 'quant_package_ids')
    def _compute_shipping_weight(self):
        for order in self:
            if order.create_package == 'auto':
                order.wk_shipping_weight = order._get_estimated_weight()
            else:
                order.wk_shipping_weight = sum([rec.shipping_weight for rec in order.quant_package_ids])

    def action_open_delivery_wizard(self):
        res = super(SaleOrder, self).action_open_delivery_wizard()
        res['context'].update({
            'default_wk_total_weight': self.wk_shipping_weight,
        })
        return res

    def auto_create_package(self):
        obj = self.filtered(lambda o:o.carrier_id)
        no_carrier = self-obj
        if len(no_carrier):
            raise ValidationError('Select Delivery Method For %s .'%(no_carrier.mapped('name')))
        for order in obj:
            order.carrier_id.wk_set_order_package(order)
        return True

    @api.model
    def wk_get_order_package(self):
        return map(lambda wk_packaging_id:dict(
            packaging_id = wk_packaging_id.packaging_id.id,
            weight = wk_packaging_id.weight,
            width=wk_packaging_id.width,
            length=wk_packaging_id.length,
            height=wk_packaging_id.height,
            cover_amount=wk_packaging_id.cover_amount,
            qty=wk_packaging_id.qty,
        ),self.wk_packaging_ids)

    def _wk_check_carrier_quotation(self,force_carrier_id=None):
        res=True

        try:
            ctx =dict(self._context)
            ctx['wk_website']=1
            res= self.with_context(ctx)._check_carrier_quotation(force_carrier_id)
        except Exception as e:
            _logger.error("Checking carrier quotation #%s" % e)
            res=False
        return res
