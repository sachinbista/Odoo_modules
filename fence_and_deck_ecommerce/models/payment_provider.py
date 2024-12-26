from odoo import models, api, fields


class PaymentAcquirer(models.Model):
    _inherit = 'payment.provider'

    is_credit_account = fields.Boolean(string='Is Credit Account', default=False)

    @api.model
    def _get_compatible_providers(self, *args, **kwargs):
        acquires = super()._get_compatible_providers(*args, **kwargs)
        if self.env.user.aquirers_to_show == 'all_minus_credit_account':
            return acquires.filtered(lambda _aq: not _aq.is_credit_account)
        if self.env.user.aquirers_to_show == 'wire_and_account_only':
            return acquires.filtered(lambda _aq: _aq.custom_mode == 'wire_transfer' or _aq.is_credit_account)
        return acquires
