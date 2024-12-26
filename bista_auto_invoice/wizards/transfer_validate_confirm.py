from odoo import models, fields


class TranferValidateConfirm(models.TransientModel):
    _name = 'transfer.validate.confirm'
    _description = "Transfer Validate Confirm"

    picking_id = fields.Many2one(comodel_name='stock.picking', required=True)
    msg = fields.Text(default="Some of the products you are attempting to deliver have not been fully invoiced and fully paid for.  Please press cancel and collect payment first.")

    def action_proceed(self):
        return self.picking_id.with_context(show_confirm=False).button_validate()
