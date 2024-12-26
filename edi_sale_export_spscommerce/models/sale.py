from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        base_edi = self.env['edi.sync.action']
        for order in self:
            if order.partner_id.outbound_edi_poa:
                sync_action = base_edi.search([('doc_type_id.doc_code', '=', 'export_sale_acknowledgement_xml')])
                if sync_action:
                    base_edi._do_doc_sync_cron(sync_action_id=sync_action, records=self)
        return res
