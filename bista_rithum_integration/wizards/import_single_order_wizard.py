##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, _


class ImportSingleOrderWizard(models.TransientModel):
    _name = 'import.single.order.wizard'
    _description = 'Import Single Order Wizard'

    po_number = fields.Char("Po Number", required=True)

    def action_import_rithum_order(self):
        rithum_config_id = self.env['rithum.config'].search([], limit=1)
        rithum_config_id.with_context(from_error=True).create_orders_single_order(self.po_number)