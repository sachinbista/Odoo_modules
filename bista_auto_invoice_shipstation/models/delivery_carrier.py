# -*- coding: utf-8 -*-
from odoo import models, _

class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def process_order(self, resource_url):
        picking_ids = super(DeliverCarrier, self).process_order(resource_url)
        if picking_ids:
            picking_ids._generate_invoice()
        return picking_ids

    

