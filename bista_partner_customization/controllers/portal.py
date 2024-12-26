from odoo.http import request

from odoo.addons.account.controllers import portal
from odoo.addons.account_payment.controllers.portal import PortalAccount


class CustomPortalAccount(PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super()._invoice_get_page_view_values(invoice, access_token, **kwargs)

        # Ensure both `providers_sudo` and `invoice` exist in values
        if not values.get("providers_sudo") or not values.get("invoice"):
            return values

        # Determine the partner: logged-in user's partner or the invoice's partner
        logged_in = not request.env.user._is_public()
        partner_sudo = request.env.user.partner_id if logged_in else invoice.partner_id

        # Retrieve payment provider IDs from the partner's invoice payment methods
        payment_method_ids = invoice.partner_id.invoice_payment_method.mapped('payment_method_id.id')

        if payment_method_ids:
            # Fetch `payment.provider` records in a single query
            payment_method_sudo = request.env['payment.method'].sudo().browse(payment_method_ids)
            payment_method_sudo = payment_method_sudo.filtered(lambda p: p.provider_ids)
            values['payment_methods_sudo'] = payment_method_sudo

            # # Retrieve compatible payment methods
            # values['payment_methods_sudo'] = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            #     provider_ids,
            #     partner_sudo.id,
            #     currency_id=invoice.currency_id.id,
            # )

        return values
