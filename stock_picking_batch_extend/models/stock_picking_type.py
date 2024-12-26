
# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import _, api, Command, fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    batch_group_by_delivery_type = fields.Boolean('Provider', help="Automatically group batches by Providers")
    batch_group_by_container = fields.Boolean('Container', help="Automatically group batches by Container")
    batch_only_assigned = fields.Boolean('Ready Pickings Only',
                                         help="Automatically group batches by Ready Pickings Only")
    batch_lock_in_progress = fields.Boolean('Batch Lock Work In Progress',
                                         help="Automatically lock batches when batch in in_progress")
    batch_processing_preferred = fields.Boolean( "Batch Processing Preferred",help="When enabled, \
                                                    this option sets batches as the recommended picking type for this operation. \
                                                    This means that the 'X Batches' button will be displayed as the default action instead of the 'X to Process'."
                                                    )

    @api.model
    def _get_batch_group_by_keys(self):
        return super()._get_batch_group_by_keys() + ['batch_group_by_container']
