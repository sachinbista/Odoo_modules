
# -*- coding: utf-8 -*-
#################################################################################
##    Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import models, fields, api

class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"
    

    wk_total_weight = fields.Float("Total Order Weight", readonly=False)

    wk_total_weight_readonly = fields.Boolean(
        compute='_compute_wk_total_weight_readonly',
        string="WK Total Weight Readonly",
    )

    @api.depends('order_id.quant_package_ids', 'order_id.wk_shipping_weight')
    def _compute_wk_total_weight_readonly(self):
        for record in self:
            if record.order_id.create_package != 'auto':
                record.wk_total_weight_readonly = len(record.order_id.quant_package_ids) > 1
            else:
                record.wk_total_weight_readonly = False


    def _get_shipment_rate(self):
        vals = self.carrier_id.with_context(order_weight=self.wk_total_weight).rate_shipment(self.order_id)
        if vals.get('success'):
            self.delivery_message = vals.get('warning_message', False)
            self.delivery_price = vals['price']
            self.display_price = vals['carrier_price']
            return {}
        return {'error_message': vals['error_message']}
