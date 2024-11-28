from odoo import models, fields, api


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        """
            This method will prepare
            default reversal dict for refunds.
            @return : vals
            @author: Yogeshwar Chaudhari @Bista Solutions Pvt. Ltd.
        """
        vals = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        if move.shopify_order_id:
            vals.update({
                        'shopify_order_id': move.shopify_order_id,
                        'sale_order_id': move.sale_order_id.id,
                        'shopify_config_id': move.shopify_config_id.id,
                        })
        return vals